from unittest.mock import patch

import numpy as np
import pytest

TOKEN = {"Authorization": "Bearer test-token"}
BASE = "/api/v1/quant"
SYMBOLS = ["AAPL", "MSFT", "BTC_USD", "TSLA"]
WEIGHTS = {"AAPL": 3, "MSFT": 3, "BTC_USD": 2, "TSLA": 2}


@pytest.fixture(scope="module")
def service(tmp_path_factory):
    from src.services import quant_risk_service

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setenv(
        "QUANT_ML_ARTIFACT_DIR", str(tmp_path_factory.mktemp("artifacts"))
    )
    quant_risk_service.reset_quant_service()
    instance = quant_risk_service.get_quant_service()
    yield instance
    quant_risk_service.reset_quant_service()
    monkeypatch.undo()


@pytest.fixture
def client(make_client, service):
    return make_client("user")


def post(client, path, body):
    return client.post(BASE + path, json=body, headers=TOKEN)


def base(**extra):
    return {"symbols": SYMBOLS, "weights": WEIGHTS, **extra}


OPERATION_PATHS = [
    "/risk/evt",
    "/risk/ml",
    "/risk/copula",
    "/risk/hybrid",
    "/risk/monte-carlo",
    "/risk/batch",
    "/risk/stress-test",
    "/risk/backtest",
    "/risk/sensitivity",
    "/risk/decomposition",
    "/risk/analysis",
    "/portfolio/search",
    "/portfolio/mean-variance",
    "/reports/risk",
]


class TestAuthentication:
    @pytest.mark.parametrize("path", OPERATION_PATHS)
    def test_operations_require_token(self, client, path):
        assert client.post(BASE + path, json=base()).status_code == 401

    @pytest.mark.parametrize(
        "path", ["/info", "/reports", "/reports/risk_20250101_000000_000000.html"]
    )
    def test_reads_require_token(self, client, path):
        assert client.get(BASE + path).status_code == 401


class TestRiskModels:
    def test_evt(self, client):
        data = post(
            client, "/risk/evt", base(confidence_levels=[0.95, 0.99])
        ).get_json()["data"]
        assert data["tail"]["exceedances"] > 10
        assert set(data["risk"]) == {"95", "99"}
        assert data["risk"]["99"]["evt"]["es"] >= data["risk"]["99"]["evt"]["var"] > 0

    def test_evt_with_returns_payload(self, client):
        rng = np.random.default_rng(0)
        returns = {
            "a": rng.standard_t(4, 400).tolist(),
            "b": rng.standard_t(4, 400).tolist(),
        }
        response = post(client, "/risk/evt", {"returns": returns, "weights": [1, 1]})
        assert response.status_code == 200

    def test_ml(self, client):
        response = post(
            client, "/risk/ml", base(model_type="rf", confidence_levels=[0.95])
        )
        data = response.get_json()["data"]
        assert response.status_code == 200 and data["model_type"] == "rf"
        forecast = data["next_period_forecast"]["95"]
        assert 0 < forecast["var"] <= forecast["es"]

    @pytest.mark.parametrize("copula", ["gaussian", "t", "clayton", "gumbel"])
    def test_copula(self, client, copula):
        data = post(
            client, "/risk/copula", base(copula_type=copula, n_scenarios=3000, seed=1)
        ).get_json()["data"]
        assert data["metrics"]["var_99"] >= data["metrics"]["var_95"] > 0
        assert set(data["correlation"]) == set(SYMBOLS)

    def test_copula_seed_reproducible(self, client):
        body = base(n_scenarios=2000, seed=4)
        assert (
            post(client, "/risk/copula", body).get_json()
            == post(client, "/risk/copula", body).get_json()
        )

    def test_hybrid(self, client):
        response = post(
            client,
            "/risk/hybrid",
            base(
                ml_model_type="rf",
                traditional_weight=0.3,
                seed=1,
                confidence_levels=[0.95],
            ),
        )
        data = response.get_json()["data"]
        assert (
            response.status_code == 200
            and data["metrics"]["es_95"] >= data["metrics"]["var_95"]
        )

    def test_monte_carlo(self, client):
        data = post(
            client, "/risk/monte-carlo", base(n_scenarios=4000, seed=2)
        ).get_json()["data"]
        assert data["n_scenarios"] == 4000
        assert data["risk_metrics"]["var_99"] >= data["risk_metrics"]["var_95"]

    def test_batch(self, client):
        data = post(
            client,
            "/risk/batch",
            base(risk_models=["historical", "evt"], confidence_levels=[0.95]),
        ).get_json()["data"]
        assert set(data["risk_metrics"]) == {"historical", "evt"}

    def test_weights_are_normalised(self, client):
        scaled = post(
            client,
            "/risk/batch",
            {
                "symbols": SYMBOLS,
                "weights": {k: v * 50 for k, v in WEIGHTS.items()},
                "risk_models": ["historical"],
            },
        ).get_json()
        plain = post(client, "/risk/batch", base(risk_models=["historical"])).get_json()
        assert scaled["data"]["risk_metrics"] == plain["data"]["risk_metrics"]


class TestEngineOperations:
    def test_stress_defaults_and_custom(self, client):
        data = post(
            client, "/risk/stress-test", base(n_custom_scenarios=20, seed=1)
        ).get_json()["data"]
        assert data["predefined_scenarios"]["crypto_crash"]["assets_affected"] == [
            "BTC_USD"
        ]
        custom = {"hit": {"description": "x", "shocks": {"AAPL": -0.5}}}
        data = post(
            client, "/risk/stress-test", base(scenarios=custom, n_custom_scenarios=5)
        ).get_json()["data"]
        assert data["predefined_scenarios"]["hit"]["portfolio_return"] == pytest.approx(
            -0.5 * 0.3
        )

    def test_backtest(self, client):
        data = post(
            client, "/risk/backtest", base(risk_models=["historical"], step_size=60)
        ).get_json()["data"]
        summary = data["summary"]["historical"]
        assert 0.02 < summary["breach_rate"] < 0.1 and data["window_count"] >= len(
            data["windows"]
        )

    def test_sensitivity(self, client):
        data = post(
            client, "/risk/sensitivity", base(shock_range=[-0.2, 0.2], n_points=5)
        ).get_json()["data"]
        assert data["sensitivities"]["AAPL"]["return_sensitivity"] == pytest.approx(0.3)

    @pytest.mark.parametrize("measure", ["volatility", "var", "es"])
    def test_decomposition(self, client, measure):
        data = post(
            client, "/risk/decomposition", base(risk_measure=measure)
        ).get_json()["data"]
        assert sum(data["percentage_contributions"]) == pytest.approx(1.0, rel=1e-6)

    def test_analysis(self, client):
        data = post(
            client,
            "/risk/analysis",
            {"symbols": SYMBOLS, "n_simulations": 1000, "seed": 1},
        ).get_json()["data"]
        assert set(data) == {
            "correlation_matrix",
            "historical_var",
            "monte_carlo_var",
            "garch_volatility",
            "stress_loss",
        }

    def test_portfolio_search(self, client):
        data = post(
            client,
            "/portfolio/search",
            {"symbols": SYMBOLS, "n_portfolios": 400, "seed": 1, "target_return": 0.2},
        ).get_json()["data"]
        assert "all_portfolios" not in data and len(data["efficient_frontier"]) >= 2
        assert "target_return" in data["target_portfolios"]

    def test_mean_variance(self, client):
        response = post(
            client,
            "/portfolio/mean-variance",
            {"symbols": SYMBOLS, "max_weight": 0.5, "portfolio_value": 50000},
        )
        data = response.get_json()["data"]
        assert response.status_code == 200
        assert max(data["max_sharpe_weights"].values()) <= 0.5 + 1e-6
        assert data["discrete_allocation"]["leftover"] >= 0


class TestReports:
    def test_generate_list_fetch(self, client):
        generated = post(
            client, "/reports/risk", base(title="Desk <b>Report</b>")
        ).get_json()["data"]
        assert (
            "<script>" not in generated["html"]
            and "&lt;b&gt;Report&lt;/b&gt;" in generated["html"]
        )
        report_id = generated["report_id"]
        listing = client.get(BASE + "/reports?limit=5", headers=TOKEN).get_json()[
            "data"
        ]["reports"]
        assert report_id in [item["report_id"] for item in listing]
        fetched = client.get(f"{BASE}/reports/{report_id}", headers=TOKEN)
        assert (
            fetched.status_code == 200
            and fetched.get_json()["data"]["html"] == generated["html"]
        )

    def test_pdf_report_and_retrieval(self, client):
        generated = post(
            client, "/reports/risk", base(title="PDF Desk", format="pdf")
        ).get_json()["data"]
        import base64

        pdf = base64.b64decode(generated["pdf_base64"])
        assert (
            pdf.startswith(b"%PDF")
            and generated["format"] == "pdf"
            and generated["report_id"].endswith(".pdf")
        )
        fetched = client.get(
            f"{BASE}/reports/{generated['report_id']}", headers=TOKEN
        ).get_json()["data"]
        assert base64.b64decode(fetched["pdf_base64"]) == pdf

    def test_delivery_is_not_claimed_without_smtp(self, client, monkeypatch):
        for name in ("QUANT_ML_SMTP_HOST", "QUANT_ML_SMTP_SENDER"):
            monkeypatch.delenv(name, raising=False)
        data = post(
            client, "/reports/risk", base(recipients=["ops@example.com"])
        ).get_json()["data"]
        assert data["delivery"] == {
            "delivered": False,
            "error": "Email delivery is not configured",
        }

    def test_delivery_through_a_configured_transport(self, client, service):
        sent = []
        transport = (
            lambda path, recipients: sent.append((path, list(recipients))) or True
        )
        with patch(
            "src.services.quant_risk_service.EmailDelivery.from_environment",
            return_value=transport,
        ):
            data = post(
                client,
                "/reports/risk",
                base(format="pdf", recipients=["ops@example.com"]),
            ).get_json()["data"]
        assert data["delivery"] == {"delivered": True, "error": None}
        assert sent[0][0].endswith(".pdf") and sent[0][1] == ["ops@example.com"]

    @pytest.mark.parametrize(
        "extra",
        [
            {"format": "docx"},
            {"recipients": ["bad"]},
            {"recipients": "a@b.com"},
            {"recipients": ["a@b.com\r\nBcc: x@y.com"]},
        ],
    )
    def test_report_option_validation(self, client, extra):
        assert post(client, "/reports/risk", base(**extra)).status_code == 400

    @pytest.mark.parametrize(
        "report_id",
        ["..%2F..%2Fetc%2Fpasswd", "x.html", "risk_20250101_000000_000000.html"],
    )
    def test_invalid_or_unknown_report_ids(self, client, report_id):
        assert client.get(f"{BASE}/reports/{report_id}", headers=TOKEN).status_code in (
            400,
            404,
        )

    @pytest.mark.parametrize("limit", ["0", "101", "abc", "-1"])
    def test_limit_validation(self, client, limit):
        assert (
            client.get(f"{BASE}/reports?limit={limit}", headers=TOKEN).status_code
            == 400
        )


class TestValidation:
    @pytest.mark.parametrize(
        "path,body",
        [
            ("/risk/evt", {}),
            ("/risk/evt", {"symbols": SYMBOLS, "returns": {"a": [0.0] * 40}}),
            ("/risk/evt", {"symbols": []}),
            ("/risk/evt", {"symbols": ["../x"]}),
            ("/risk/evt", {"symbols": SYMBOLS, "weights": {"AAPL": -1}}),
            ("/risk/evt", {"symbols": SYMBOLS, "weights": {"AAPL": 0}}),
            ("/risk/evt", {"symbols": SYMBOLS, "weights": []}),
            ("/risk/evt", {"symbols": SYMBOLS, "threshold_quantile": 0.9}),
            ("/risk/evt", {"symbols": SYMBOLS, "confidence_levels": [1.2]}),
            ("/risk/evt", {"symbols": SYMBOLS, "confidence_levels": []}),
            ("/risk/evt", {"returns": {"a": [0.1] * 10}}),
            ("/risk/evt", {"returns": {"a": [0.1] * 40, "b": [0.1] * 41}}),
            ("/risk/evt", {"returns": {"a": ["x"] * 40}}),
            ("/risk/evt", {"returns": {"<bad>": [0.1] * 40}}),
            ("/risk/ml", {"symbols": SYMBOLS, "model_type": "xgb"}),
            ("/risk/ml", {"symbols": SYMBOLS, "feature_window": 2}),
            ("/risk/copula", {"symbols": SYMBOLS, "copula_type": "frank"}),
            ("/risk/copula", {"symbols": SYMBOLS, "n_scenarios": 10**7}),
            ("/risk/copula", {"symbols": SYMBOLS, "seed": -1}),
            ("/risk/hybrid", {"symbols": SYMBOLS, "traditional_weight": 2}),
            ("/risk/batch", {"symbols": SYMBOLS, "risk_models": ["garch"]}),
            (
                "/risk/stress-test",
                {"symbols": SYMBOLS, "scenarios": {"x": {"shocks": {}}}},
            ),
            (
                "/risk/stress-test",
                {"symbols": SYMBOLS, "scenarios": {"x": {"shocks": {"all": -5}}}},
            ),
            ("/risk/stress-test", {"symbols": SYMBOLS, "n_custom_scenarios": 0}),
            ("/risk/backtest", {"symbols": SYMBOLS, "window_size": 5}),
            ("/risk/backtest", {"symbols": SYMBOLS, "window_size": 5000}),
            ("/risk/sensitivity", {"symbols": SYMBOLS, "shock_range": [0.2, -0.2]}),
            ("/risk/sensitivity", {"symbols": SYMBOLS, "shock_range": [1]}),
            ("/risk/decomposition", {"symbols": SYMBOLS, "risk_measure": "beta"}),
            ("/risk/analysis", {"symbols": SYMBOLS, "horizon": 500}),
            ("/portfolio/search", {"symbols": ["AAPL"]}),
            ("/portfolio/search", {"symbols": SYMBOLS, "risk_model": "x"}),
            ("/portfolio/mean-variance", {"symbols": ["AAPL"]}),
            ("/portfolio/mean-variance", {"symbols": SYMBOLS, "max_weight": 0.1}),
            ("/portfolio/mean-variance", {"symbols": SYMBOLS, "risk_free_rate": 5}),
            ("/reports/risk", {"symbols": SYMBOLS, "title": ""}),
            ("/reports/risk", {"symbols": SYMBOLS, "title": "x" * 200}),
        ],
    )
    def test_invalid_requests_return_400(self, client, path, body):
        response = post(client, path, body)
        assert response.status_code == 400, response.get_json()
        assert response.get_json()["status"] == "error"

    def test_unknown_symbol_and_weight_asset(self, client):
        assert (
            post(client, "/risk/evt", {"symbols": ["AAPL", "NOSUCH"]}).status_code
            == 400
        )
        assert (
            post(
                client, "/risk/evt", {"symbols": SYMBOLS, "weights": {"ZZZ": 1}}
            ).status_code
            == 400
        )

    def test_non_json_body(self, client):
        assert (
            client.post(BASE + "/risk/evt", data="x", headers=TOKEN).status_code == 400
        )

    def test_unexpected_failure_is_500(self, client, service):
        with patch.object(
            service.engine,
            "parallel_batch_risk_calculation",
            side_effect=RuntimeError("boom"),
        ):
            assert post(client, "/risk/batch", base()).status_code == 500

    def test_numerical_failure_is_422(self, client, service):
        with patch.object(
            service.engine,
            "parallel_batch_risk_calculation",
            side_effect=ArithmeticError("no convergence"),
        ):
            response = post(client, "/risk/batch", base())
        assert response.status_code == 422


class TestInfo:
    def test_info(self, client):
        data = client.get(BASE + "/info", headers=TOKEN).get_json()["data"]
        assert "AAPL" in data["available_symbols"]
        assert data["limits"]["max_assets"] == 50
        assert set(data["copula_types"]) == {"gaussian", "t", "clayton", "gumbel"}
        assert data["report_formats"] == ["html", "pdf"] and isinstance(
            data["report_delivery_configured"], bool
        )
