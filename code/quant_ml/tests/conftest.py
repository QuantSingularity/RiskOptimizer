import numpy as np
import pandas as pd
import pytest
from scipy import stats


@pytest.fixture(scope="session")
def prices():
    rng = np.random.default_rng(7)
    index = pd.bdate_range("2021-01-01", periods=400)
    drift = np.array([0.0006, 0.0004, 0.0002, 0.0005])
    vol = np.array([0.02, 0.015, 0.008, 0.025])
    returns = rng.normal(drift, vol, size=(400, 4))
    return pd.DataFrame(
        100 * np.cumprod(1 + returns, axis=0),
        index=index,
        columns=["AAA", "BBB", "CCC", "DDD"],
    )


@pytest.fixture(scope="session")
def returns_frame():
    rng = np.random.default_rng(11)
    n = 900
    common = stats.t.rvs(4, size=n, random_state=rng) * 0.008
    columns = {}
    for i, (beta, idio) in enumerate([(1.0, 0.006), (0.8, 0.008), (1.2, 0.01)]):
        columns[f"A{i}"] = (
            0.0004 + beta * common + stats.t.rvs(5, size=n, random_state=rng) * idio
        )
    return pd.DataFrame(columns, index=pd.bdate_range("2020-01-01", periods=n))


@pytest.fixture(scope="session")
def real_returns():
    from data.loaders import available_symbols, load_close_prices

    return load_close_prices(available_symbols()).pct_change().dropna()


@pytest.fixture(scope="session")
def t_losses():
    return stats.t.rvs(4, size=100_000, random_state=1) * 0.01


@pytest.fixture
def artifact_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("QUANT_ML_ARTIFACT_DIR", str(tmp_path))
    return tmp_path


class FakeSmtpServer:
    def __init__(self):
        import socketserver
        import threading

        outer = self
        self.messages = []
        self.refused = set()
        self.commands = []

        class Handler(socketserver.StreamRequestHandler):
            def reply(self, text):
                self.wfile.write((text + "\r\n").encode())

            def handle(self):
                self.reply("220 test ready")
                envelope = {"to": []}
                while True:
                    line = self.rfile.readline()
                    if not line:
                        return
                    text = line.decode(errors="replace").strip()
                    outer.commands.append(text.split(" ")[0].upper())
                    command = text.upper()
                    if command.startswith(("EHLO", "HELO")):
                        self.reply("250 localhost")
                    elif command.startswith("MAIL FROM"):
                        envelope = {"from": text[10:], "to": []}
                        self.reply("250 OK")
                    elif command.startswith("RCPT TO"):
                        address = text[8:].strip("<>")
                        if address.lower() in outer.refused:
                            self.reply("550 no such user")
                        else:
                            envelope["to"].append(address)
                            self.reply("250 OK")
                    elif command == "DATA":
                        self.reply("354 go ahead")
                        lines = []
                        while True:
                            data_line = self.rfile.readline()
                            if data_line in (b".\r\n", b""):
                                break
                            lines.append(data_line)
                        envelope["data"] = b"".join(lines)
                        outer.messages.append(envelope)
                        self.reply("250 queued")
                    elif command == "QUIT":
                        self.reply("221 bye")
                        return
                    else:
                        self.reply("250 OK")

        class Server(socketserver.ThreadingTCPServer):
            allow_reuse_address = True
            daemon_threads = True

        self.server = Server(("127.0.0.1", 0), Handler)
        self.host, self.port = self.server.server_address
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def environment(self, **extra):
        values = {
            "QUANT_ML_SMTP_HOST": self.host,
            "QUANT_ML_SMTP_PORT": str(self.port),
            "QUANT_ML_SMTP_SENDER": "reports@example.com",
            "QUANT_ML_SMTP_TLS": "false",
        }
        values.update(extra)
        return values

    def close(self):
        self.server.shutdown()
        self.server.server_close()


@pytest.fixture
def smtp_server():
    server = FakeSmtpServer()
    yield server
    server.close()


@pytest.fixture
def no_smtp_environment(monkeypatch):
    for name in list(__import__("os").environ):
        if name.startswith("QUANT_ML_SMTP_"):
            monkeypatch.delenv(name)
