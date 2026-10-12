from unittest.mock import patch

import pytest

TOKEN = {"Authorization": "Bearer test-token"}
SYMBOLS = ["AAPL", "MSFT", "BTC_USD"]


@pytest.fixture(scope="module")
def service(tmp_path_factory):
    from src.services import ai_optimization

    path = tmp_path_factory.mktemp("model") / "trained_model.joblib"
    with patch.object(ai_optimization, "MODEL_PATH", str(path)):
        ai_optimization.reset_ai_service()
        instance = ai_optimization.get_ai_service()
        yield instance
        ai_optimization.reset_ai_service()


@pytest.fixture
def client(make_client, service):
    return make_client("user")


def post(client, path, body, headers=TOKEN):
    return client.post(f"/api/v1/optimization{path}", json=body, headers=headers)


class TestAuthentication:
    @pytest.mark.parametrize(
        "method,path",
        [
            ("post", "/optimize"),
            ("post", "/efficient-frontier"),
            ("post", "/simulate"),
            ("post", "/sentiment"),
            ("get", "/forecast/AAPL"),
            ("get", "/symbols"),
            ("get", "/constraints"),
            ("get", "/model"),
        ],
    )
    def test_requires_token(self, client, method, path):
        response = getattr(client, method)(f"/api/v1/optimization{path}")
        assert response.status_code == 401

    def test_training_requires_admin(self, client):
        response = post(client, "/model/train", {})
        assert response.status_code == 403


class TestOptimize:
    def test_optimize_with_symbols(self, client):
        response = post(client, "/optimize", {"symbols": SYMBOLS, "risk_tolerance": 4})
        assert response.status_code == 200
        data = response.get_json()["data"]
        assert set(data["optimized_allocation"]) == set(SYMBOLS)
        assert abs(sum(data["optimized_allocation"].values()) - 1) < 1e-6
        assert data["model_type"] == "ml"
        assert data["risk_tolerance"] == 4

    def test_optimize_with_market_data(self, client):
        base = [100 + i * 0.3 + (i % 5) for i in range(80)]
        other = [50 + i * 0.1 + (i % 7) * 0.5 for i in range(80)]
        response = post(
            client, "/optimize", {"market_data": {"AAA": base, "BBB": other}}
        )
        assert response.status_code == 200
        assert set(response.get_json()["data"]["optimized_allocation"]) == {
            "AAA",
            "BBB",
        }

    def test_weight_cap_and_method(self, client):
        response = post(
            client,
            "/optimize",
            {
                "symbols": ["AAPL", "MSFT", "AMZN", "GOOGL", "TSLA"],
                "max_weight": 0.3,
                "method": "max_sharpe",
            },
        )
        assert response.status_code == 200
        weights = response.get_json()["data"]["optimized_allocation"]
        assert max(weights.values()) <= 0.3 + 1e-6

    @pytest.mark.parametrize(
        "body",
        [
            {},
            {"symbols": ["AAPL"]},
            {"symbols": SYMBOLS, "risk_tolerance": 0},
            {"symbols": SYMBOLS, "risk_tolerance": 11},
            {"symbols": SYMBOLS, "risk_tolerance": "5"},
            {"symbols": SYMBOLS, "risk_tolerance": True},
            {"symbols": SYMBOLS, "method": "bogus"},
            {"symbols": SYMBOLS, "min_weight": 0.8, "max_weight": 0.2},
            {"symbols": ["AAPL", "../../etc"]},
            {"symbols": ["AAPL", "NOSUCH"]},
            {"symbols": SYMBOLS, "max_weight": 0.2},
            {"market_data": {"A": [1, 2, 3]}},
            {"market_data": {}},
        ],
    )
    def test_invalid_requests_return_400(self, client, body):
        response = post(client, "/optimize", body)
        assert response.status_code == 400
        assert response.get_json()["status"] == "error"

    def test_non_json_body_rejected(self, client):
        response = client.post(
            "/api/v1/optimization/optimize", data="nope", headers=TOKEN
        )
        assert response.status_code == 400

    def test_unexpected_failure_is_500_not_401(self, client, service):
        with patch.object(service, "optimize_portfolio", side_effect=RuntimeError("x")):
            response = post(client, "/optimize", {"symbols": SYMBOLS})
        assert response.status_code == 500


class TestFrontierAndSimulation:
    def test_frontier(self, client):
        response = post(
            client, "/efficient-frontier", {"symbols": SYMBOLS, "points": 6}
        )
        assert response.status_code == 200
        frontier = response.get_json()["data"]["frontier"]
        assert len(frontier) >= 2
        assert {"expected_return", "volatility", "weights"} <= set(frontier[0])

    def test_frontier_points_validated(self, client):
        assert (
            post(
                client, "/efficient-frontier", {"symbols": SYMBOLS, "points": 1}
            ).status_code
            == 400
        )

    def test_simulation_with_symbols_from_weights(self, client):
        response = post(
            client,
            "/simulate",
            {
                "weights": {"AAPL": 0.5, "MSFT": 0.5},
                "num_simulations": 300,
                "time_horizon": 60,
                "initial_value": 5000,
                "seed": 1,
            },
        )
        assert response.status_code == 200
        data = response.get_json()["data"]
        assert data["simulation_summary"]["initial_value"] == 5000
        assert set(data["simulation_summary"]["percentiles"]) == {
            "p5",
            "p25",
            "p50",
            "p75",
            "p95",
        }
        metrics = data["risk_metrics"]
        assert metrics["value_at_risk_99"] >= metrics["value_at_risk_95"] >= 0

    def test_single_asset_simulation_allowed(self, client):
        response = post(
            client,
            "/simulate",
            {"weights": {"AAPL": 1.0}, "num_simulations": 50, "time_horizon": 20},
        )
        assert response.status_code == 200

    def test_simulation_is_seeded(self, client):
        body = {
            "weights": {"AAPL": 1.0, "MSFT": 1.0},
            "num_simulations": 100,
            "seed": 5,
        }
        first = post(client, "/simulate", body).get_json()
        second = post(client, "/simulate", body).get_json()
        assert first == second

    @pytest.mark.parametrize(
        "body",
        [
            {},
            {"weights": {}},
            {"weights": {"AAPL": -1}},
            {"weights": {"AAPL": 0}},
            {"weights": {"AAPL": 1}, "num_simulations": 10**7},
            {"weights": {"AAPL": 1}, "time_horizon": 0},
            {"weights": {"AAPL": 1}, "initial_value": -5},
            {"weights": {"NOSUCH": 1}},
        ],
    )
    def test_invalid_simulation_requests(self, client, body):
        assert post(client, "/simulate", body).status_code == 400


class TestForecastSentimentMeta:
    def test_forecast(self, client):
        response = client.get(
            "/api/v1/optimization/forecast/aapl?periods=5", headers=TOKEN
        )
        assert response.status_code == 200
        data = response.get_json()["data"]
        assert data["ticker"] == "AAPL" and len(data["forecast"]) == 5
        assert data["requested_model"] == "auto"
        assert data["model"] in ("naive", "drift", "ets")
        assert data["validation"]["scores"]["naive"] > 0
        assert data["beats_naive"] is (data["model"] != "naive")

    def test_forecast_explicit_model_and_warning_free_baseline(self, client):
        response = client.get(
            "/api/v1/optimization/forecast/BTC_USD?periods=5&model=ets", headers=TOKEN
        )
        data = response.get_json()["data"]
        assert response.status_code == 200 and data["model"] == "ets"
        assert data["frequency"] == "D"

    @pytest.mark.parametrize("model", ["arima", "AUTO", "", "naive;drop"])
    def test_forecast_rejects_unknown_models(self, client, model):
        response = client.get(
            f"/api/v1/optimization/forecast/AAPL?model={model}", headers=TOKEN
        )
        assert response.status_code == 400

    @pytest.mark.parametrize(
        "path", ["AAPL?periods=0", "AAPL?periods=999", "AAPL?periods=abc", "NOSUCH"]
    )
    def test_forecast_validation(self, client, path):
        response = client.get(f"/api/v1/optimization/forecast/{path}", headers=TOKEN)
        assert response.status_code == 400

    def test_sentiment(self, client):
        response = post(
            client,
            "/sentiment",
            {"texts": ["Stocks surge in a strong rally", "Firm faces bankruptcy"]},
        )
        if response.status_code == 503:
            pytest.skip("VADER lexicon unavailable")
        assert response.status_code == 200
        data = response.get_json()["data"]
        assert [i["sentiment"] for i in data["items"]] == ["Positive", "Negative"]
        assert data["summary"]["count"] == 2

    @pytest.mark.parametrize(
        "body",
        [{}, {"texts": []}, {"texts": [1]}, {"texts": [""]}, {"texts": ["x" * 2001]}],
    )
    def test_sentiment_validation(self, client, body):
        assert post(client, "/sentiment", body).status_code == 400

    def test_symbols_constraints_and_model(self, client):
        symbols = client.get("/api/v1/optimization/symbols", headers=TOKEN)
        assert "AAPL" in symbols.get_json()["data"]["symbols"]
        constraints = client.get("/api/v1/optimization/constraints", headers=TOKEN)
        assert constraints.get_json()["data"]["risk_tolerance"]["max"] == 10
        info = client.get("/api/v1/optimization/model", headers=TOKEN).get_json()[
            "data"
        ]
        assert info["mode"] == "ml" and info["model_loaded"] is True

    def test_admin_can_train(self, make_client, service):
        admin = make_client("admin")
        response = post(admin, "/model/train", {"symbols": SYMBOLS})
        assert response.status_code == 200
        assert "prediction_metrics" in response.get_json()["data"]


class TestServiceFallback:
    def test_classical_mode_when_training_disabled(self, tmp_path):
        from src.services.ai_optimization import AIOptimizationService

        instance = AIOptimizationService(
            str(tmp_path / "none.joblib"), auto_train=False
        )
        assert instance.mode == "classical"
        result = instance.optimize_portfolio(symbols=SYMBOLS)
        assert result["model_type"] == "classical"
        assert instance.get_model_info()["model_loaded"] is False

    def test_corrupt_model_file_falls_back_and_reports(self, tmp_path):
        from src.services.ai_optimization import AIOptimizationService

        broken = tmp_path / "bad.joblib"
        broken.write_bytes(b"not a model")
        instance = AIOptimizationService(str(broken), auto_train=False)
        assert instance.mode == "classical"
        assert instance.get_model_info()["load_error"]
