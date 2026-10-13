import json

import pytest
from training import benchmark as benchmark_module
from training.benchmark import benchmark, evt_accuracy, main

SYMBOLS = ["AAPL", "MSFT", "GOOGL", "BTC_USD"]


@pytest.fixture
def stub_evaluation(monkeypatch):
    monkeypatch.setattr(
        benchmark_module,
        "evaluate",
        lambda symbols: {"data": {"assets": list(symbols)}, "passed": True},
    )


class TestBenchmark:
    def test_quick_benchmark_structure(self, stub_evaluation):
        result = benchmark(SYMBOLS, quick=True)
        assert result["quick"] is True and result["evaluation"]["passed"] is True
        assert {row["degrees_of_freedom"] for row in result["evt_accuracy"]} == {
            3,
            4,
            6,
        }
        assert set(result["copula_fit"]["models"]) == {
            "gaussian",
            "t",
            "clayton",
            "gumbel",
        }
        assert result["engine_timing"][0]["n_jobs"] == 1
        assert result["engine_timing"][0]["monte_carlo"]["seconds"] > 0
        assert "available" in result["prophet_comparison"]

    def test_evt_estimates_track_the_truth(self):
        for row in evt_accuracy(60_000):
            assert abs(row["relative_error"]) < 0.08

    def test_copula_fit_reports_the_empirical_baseline(self, stub_evaluation):
        fit = benchmark(SYMBOLS, quick=True)["copula_fit"]
        assert fit["empirical"]["var_99"] > fit["empirical"]["var_95"] > 0
        for name in ("gaussian", "t"):
            ratio = fit["models"][name]["var_95"] / fit["empirical"]["var_95"]
            assert 0.8 < ratio < 1.2

    def test_cli_writes_strict_json(self, stub_evaluation, tmp_path):
        output = tmp_path / "benchmark.json"
        assert main(["--symbols", *SYMBOLS, "--quick", "--output", str(output)]) == 0
        loaded = json.loads(output.read_text())
        assert loaded["quick"] is True and loaded["engine_timing"]
