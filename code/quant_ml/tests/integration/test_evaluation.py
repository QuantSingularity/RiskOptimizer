import json

import pytest
from training.evaluate import evaluate, main

SYMBOLS = ["AAPL", "MSFT", "GOOGL", "BTC_USD"]


@pytest.fixture(scope="module")
def report():
    return evaluate(SYMBOLS)


class TestEvaluate:
    def test_report_structure(self, report):
        assert (
            report["data"]["assets"] == SYMBOLS
            and report["data"]["observations"] > 1000
        )
        assert set(report) >= {
            "optimizer",
            "ml_risk",
            "backtests",
            "forecasts",
            "checks",
            "passed",
        }
        assert set(report["ml_risk"]) == {"gbm", "rf", "nn"}
        assert set(report["backtests"]) == {"parametric", "historical", "evt"}
        assert set(report["forecasts"]) == set(SYMBOLS)

    def test_models_are_calibrated_on_real_data(self, report):
        for name, item in report["ml_risk"].items():
            assert abs(item["coverage"] - item["target"]) <= 0.06, name
        for name, item in report["backtests"].items():
            assert item["kupiec_pvalue"] > 0.01, name
        assert report["passed"] is True

    def test_forecast_summaries_include_the_baseline(self, report):
        for item in report["forecasts"].values():
            assert item["scores"]["naive"] > 0 and item["windows"] >= 2
            assert item["beats_naive"] is (item["selected_model"] != "naive")


class TestCli:
    def test_writes_strict_json_and_exits_zero(self, tmp_path):
        output = tmp_path / "report.json"
        assert main(["--symbols", *SYMBOLS, "--output", str(output)]) == 0
        loaded = json.loads(output.read_text())
        assert loaded["passed"] is True

    def test_strict_mode_fails_an_impossible_tolerance(self, tmp_path):
        output = tmp_path / "strict.json"
        assert (
            main(
                [
                    "--symbols",
                    *SYMBOLS,
                    "--tolerance",
                    "0",
                    "--strict",
                    "--output",
                    str(output),
                ]
            )
            == 1
        )
        assert (
            main(["--symbols", *SYMBOLS, "--tolerance", "0", "--output", str(output)])
            == 0
        )

    def test_prints_to_stdout_without_output(self, capsys):
        assert main(["--symbols", *SYMBOLS]) == 0
        assert json.loads(capsys.readouterr().out)["data"]["assets"] == SYMBOLS
