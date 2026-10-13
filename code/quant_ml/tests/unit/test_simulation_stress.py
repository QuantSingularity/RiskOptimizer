import numpy as np
import pytest
from risk.simulation import MAX_DRAWS, simulate_portfolio_paths
from risk.stress import SCENARIO_TYPES, stress_portfolio

WEIGHTS = [0.5, 0.3, 0.2]


class TestPathSimulation:
    @pytest.fixture(scope="class")
    def result(self, returns_frame):
        return simulate_portfolio_paths(returns_frame, WEIGHTS, 5000, 60, seed=1)

    def test_terminal_mean_matches_compounded_history(self, result, returns_frame):
        daily = (returns_frame.to_numpy() @ np.array(WEIGHTS)).mean()
        assert result["statistics"]["mean_final_value"] == pytest.approx(
            np.exp(60 * daily), rel=0.03
        )

    def test_risk_metrics_are_ordered(self, result):
        risk = result["risk_metrics"]
        assert risk["cvar_95"] >= risk["var_95"] > 0
        assert risk["var_99"] >= risk["var_95"]
        assert 0 < risk["probability_of_loss"] < 1

    def test_drawdown_is_a_real_drawdown(self, result):
        drawdown = result["drawdown"]
        assert (
            drawdown["worst_max_drawdown"]
            <= drawdown["p95_worst_max_drawdown"]
            <= drawdown["mean_max_drawdown"]
            <= 0
        )
        assert all(-1.0 <= d <= 0 for d in result["simulation_data"]["max_drawdowns"])

    def test_percentiles_are_monotone(self, result):
        values = list(result["percentiles"].values())
        assert values == sorted(values)

    def test_seeded_runs_are_identical(self, returns_frame):
        first = simulate_portfolio_paths(returns_frame, WEIGHTS, 500, 20, seed=9)
        second = simulate_portfolio_paths(returns_frame, WEIGHTS, 500, 20, seed=9)
        assert first["simulation_data"] == second["simulation_data"]

    def test_sample_is_capped(self, returns_frame):
        data = simulate_portfolio_paths(
            returns_frame, WEIGHTS, 2000, 5, seed=1, keep=50
        )["simulation_data"]
        assert len(data["final_values"]) == 50

    def test_path_values_stay_positive_under_extreme_returns(self):
        rng = np.random.default_rng(0)
        wild = rng.standard_t(1.5, size=(300, 2)) * 0.2
        out = simulate_portfolio_paths(
            np.clip(wild, -0.9, None), [0.5, 0.5], 500, 50, seed=1
        )
        assert out["statistics"]["min_final_value"] > 0

    @pytest.mark.parametrize(
        "kwargs",
        [
            {"n_paths": 0},
            {"horizon": 0},
            {"horizon": 5000},
            {"n_paths": True},
            {"copula_type": "frank"},
            {"confidence_levels": [1.2]},
            {"n_paths": 200_000, "horizon": 2000},
        ],
    )
    def test_validation(self, returns_frame, kwargs):
        with pytest.raises(ValueError):
            simulate_portfolio_paths(returns_frame, WEIGHTS, **kwargs)

    def test_draw_budget_is_enforced(self):
        assert MAX_DRAWS == 5_000_000


class TestStress:
    @pytest.fixture(scope="class")
    def outcome(self, returns_frame):
        scenarios = [
            {"type": "market_crash", "shock": -0.3},
            {"type": "volatility_spike", "multiplier": 2.0},
            {"type": "correlation_breakdown", "intensity": 0.9},
        ]
        return stress_portfolio(returns_frame, WEIGHTS, scenarios, seed=1)

    def test_crash_is_a_single_shock_not_a_shift_of_every_day(self, outcome):
        crash = outcome["stress_results"][0]
        base = outcome["baseline"]
        assert crash["stressed_return"] == pytest.approx(base["return"] - 0.3)
        assert crash["stressed_volatility"] == pytest.approx(base["volatility"])
        assert crash["stressed_var_95"] > base["var_95"]

    def test_volatility_spike_scales_volatility_but_not_the_mean(self, outcome):
        spike = outcome["stress_results"][1]
        assert spike["stressed_volatility"] == pytest.approx(
            2 * outcome["baseline"]["volatility"], rel=1e-6
        )
        assert spike["stressed_return"] == pytest.approx(
            outcome["baseline"]["return"], abs=1e-9
        )

    def test_correlation_breakdown_lowers_portfolio_volatility_for_positive_correlation(
        self, outcome
    ):
        assert (
            outcome["stress_results"][2]["stressed_volatility"]
            < outcome["baseline"]["volatility"]
        )

    def test_impacts_are_differences(self, outcome):
        for item in outcome["stress_results"]:
            assert item["return_impact"] == pytest.approx(
                item["stressed_return"] - outcome["baseline"]["return"]
            )
            assert item["volatility_impact"] == pytest.approx(
                item["stressed_volatility"] - outcome["baseline"]["volatility"]
            )

    def test_legacy_noise_level_alias(self, returns_frame):
        result = stress_portfolio(
            returns_frame,
            WEIGHTS,
            [{"type": "correlation_breakdown", "noise_level": 0.1}],
            seed=1,
        )
        assert result["stress_results"][0]["stressed_volatility"] > 0

    def test_seed_reproducible(self, returns_frame):
        scenario = [{"type": "correlation_breakdown", "intensity": 0.5}]
        assert stress_portfolio(
            returns_frame, WEIGHTS, scenario, seed=4
        ) == stress_portfolio(returns_frame, WEIGHTS, scenario, seed=4)

    @pytest.mark.parametrize(
        "scenarios",
        [
            [],
            "x",
            ["not a dict"],
            [{"type": "meteor"}],
            [{}],
            [{"type": "market_crash", "shock": -5}],
            [{"type": "volatility_spike", "multiplier": 0}],
            [{"type": "volatility_spike", "multiplier": 99}],
            [{"type": "correlation_breakdown", "intensity": 2}],
        ],
    )
    def test_validation(self, returns_frame, scenarios):
        with pytest.raises(ValueError):
            stress_portfolio(returns_frame, WEIGHTS, scenarios)

    def test_scenario_types_listed(self):
        assert set(SCENARIO_TYPES) == {
            "market_crash",
            "volatility_spike",
            "correlation_breakdown",
        }
