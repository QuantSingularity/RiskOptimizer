import numpy as np
import pytest
from risk.evt import ExtremeValueRisk
from scipy import stats


@pytest.fixture(scope="module")
def pot(t_losses):
    return ExtremeValueRisk(seed=0).fit_pot(t_losses, threshold_quantile=0.05)


@pytest.fixture(scope="module")
def block(t_losses):
    model = ExtremeValueRisk(seed=0)
    model.fit_block_maxima(t_losses, 20)
    return model


class TestFitting:
    def test_pot_params(self, pot):
        assert pot.fitted
        assert pot.pot_params["shape"] == pytest.approx(0.25, abs=0.12)
        assert pot.pot_params["tail_fraction"] == pytest.approx(0.05, abs=0.001)
        assert pot.gpd_params == (pot.pot_params["shape"], pot.pot_params["scale"])

    def test_explicit_threshold(self, t_losses):
        model = ExtremeValueRisk().fit_pot(t_losses, threshold=-0.02)
        assert model.pot_params["loss_threshold"] == pytest.approx(0.02)

    def test_inputs_series_and_frame(self, t_losses):
        import pandas as pd

        assert ExtremeValueRisk().fit_pot(pd.Series(t_losses)).fitted
        assert ExtremeValueRisk().fit_pot(pd.DataFrame({"a": t_losses})).fitted

    @pytest.mark.parametrize("q", [0, 0.5, -0.1, 0.9])
    def test_bad_threshold_quantile(self, t_losses, q):
        with pytest.raises(ValueError):
            ExtremeValueRisk().fit_pot(t_losses, threshold_quantile=q)

    def test_too_little_data(self):
        with pytest.raises(ValueError):
            ExtremeValueRisk().fit_pot(np.arange(5.0))

    def test_block_maxima(self, block):
        assert block.bm_params["shape"] == pytest.approx(0.2, abs=0.15)
        assert len(block.bm_params["block_maxima"]) == 5000

    def test_block_size_validation(self, t_losses):
        with pytest.raises(ValueError):
            ExtremeValueRisk().fit_block_maxima(t_losses, 1)
        with pytest.raises(ValueError):
            ExtremeValueRisk().fit_block_maxima(t_losses[:30], 20)


class TestVarEs:
    @pytest.mark.parametrize("confidence", [0.95, 0.99, 0.995])
    def test_pot_var_matches_truth(self, pot, confidence):
        truth = -stats.t.ppf(1 - confidence, 4) * 0.01
        assert pot.calculate_var(confidence) == pytest.approx(truth, rel=0.06)

    @pytest.mark.parametrize("confidence", [0.95, 0.99, 0.995])
    def test_block_maxima_var_uses_daily_confidence(self, block, confidence):
        truth = -stats.t.ppf(1 - confidence, 4) * 0.01
        assert block.calculate_var(confidence) == pytest.approx(truth, rel=0.1)

    def test_pot_es_matches_truth(self, pot):
        q = stats.t.ppf(0.01, 4)
        truth = stats.t.pdf(q, 4) * (4 + q**2) / 3 / 0.01 * 0.01
        assert pot.calculate_es(0.99) == pytest.approx(truth, rel=0.1)

    def test_normal_method_handles_nonzero_mean(self, t_losses):
        data = t_losses + 0.005
        model = ExtremeValueRisk().fit_pot(data)
        z = stats.norm.ppf(0.95)
        assert model.calculate_var(0.95, "normal") == pytest.approx(
            -(data.mean() - z * data.std()), rel=1e-9
        )
        assert model.calculate_es(0.95, "normal") == pytest.approx(
            -data.mean() + data.std() * stats.norm.pdf(z) / 0.05, rel=1e-9
        )

    def test_monotone_and_ordering(self, pot):
        assert (
            pot.calculate_var(0.95) < pot.calculate_var(0.99) < pot.calculate_var(0.999)
        )
        for confidence in (0.95, 0.99):
            assert pot.calculate_es(confidence) >= pot.calculate_var(confidence)

    def test_confidence_below_threshold_falls_back_to_empirical(self, pot, t_losses):
        assert pot.calculate_var(0.8) == pytest.approx(
            -np.quantile(t_losses, 0.2), rel=1e-9
        )

    def test_return_period(self, pot):
        assert pot.calculate_var(return_period=100) == pytest.approx(
            pot.calculate_var(0.99)
        )
        with pytest.raises(ValueError):
            pot.calculate_var(return_period=1)

    def test_historical_is_nonnegative_for_gains(self):
        model = ExtremeValueRisk().fit_pot(
            np.abs(np.random.default_rng(0).normal(0.01, 0.002, 500))
        )
        assert model.calculate_var(0.95, "historical") == 0.0

    def test_infinite_es_for_extreme_shape(self, t_losses):
        model = ExtremeValueRisk().fit_pot(t_losses)
        model.pot_params["shape"] = 1.2
        assert model.calculate_es(0.99) == float("inf")

    def test_errors(self, pot, t_losses):
        with pytest.raises(ValueError):
            pot.calculate_var(0.95, "bogus")
        with pytest.raises(ValueError):
            pot.calculate_es(1.0)
        with pytest.raises(ValueError):
            ExtremeValueRisk().calculate_var(0.95)
        with pytest.raises(ValueError):
            ExtremeValueRisk().calculate_es(0.95)


class TestScenarios:
    def test_evt_scenarios_lie_in_the_tail(self, pot):
        scenarios = pot.generate_scenarios(20000, "evt", "extreme")
        assert (scenarios < 0).all()
        assert (scenarios < -pot.calculate_var(0.95)).mean() > 0.99
        assert -scenarios.mean() == pytest.approx(pot.calculate_es(0.99), rel=0.1)

    def test_severity_orders_losses(self, pot):
        extreme = -pot.generate_scenarios(20000, "evt", "extreme").mean()
        mild = -pot.generate_scenarios(20000, "evt", "mild").mean()
        assert extreme > mild

    def test_seed_reproducible(self, t_losses):
        first = ExtremeValueRisk(seed=3).fit_pot(t_losses).generate_scenarios(100)
        second = ExtremeValueRisk(seed=3).fit_pot(t_losses).generate_scenarios(100)
        assert np.array_equal(first, second)

    @pytest.mark.parametrize("method", ["historical", "normal"])
    def test_other_methods(self, pot, method):
        assert len(pot.generate_scenarios(50, method)) == 50

    def test_block_maxima_scenarios(self, block):
        assert (block.generate_scenarios(100, "evt") < 0).all()

    def test_simulate_extreme_scenarios_exceed_var(self, pot):
        scenarios = pot.simulate_extreme_scenarios(100, 0.95)
        assert len(scenarios) == 100 and (scenarios > pot.calculate_var(0.95)).all()

    def test_invalid(self, pot):
        with pytest.raises(ValueError):
            pot.generate_scenarios(0)
        with pytest.raises(ValueError):
            pot.generate_scenarios(10, "bogus")


class TestTailDependence:
    def test_dependent_vs_independent(self):
        rng = np.random.default_rng(0)
        x = rng.standard_t(4, 5000)
        dependent = ExtremeValueRisk().tail_dependence(
            x, x + 0.1 * rng.standard_normal(5000)
        )
        independent = ExtremeValueRisk().tail_dependence(x, rng.standard_t(4, 5000))
        assert dependent > 0.5 > independent

    def test_copula_method_handles_perfect_correlation(self):
        x = np.random.default_rng(1).standard_normal(200)
        assert 0 <= ExtremeValueRisk().tail_dependence(x, x, method="copula") <= 1.0

    def test_validation(self):
        with pytest.raises(ValueError):
            ExtremeValueRisk().tail_dependence([1.0] * 20, [1.0] * 19)
        with pytest.raises(ValueError):
            ExtremeValueRisk().tail_dependence(
                np.arange(20.0), np.arange(20.0), method="x"
            )


class TestPlots:
    def test_plots_return_figures(self, pot):
        import matplotlib.pyplot as plt

        for figure in (
            pot.plot_tail_distribution(),
            pot.plot_mean_excess(),
            pot.plot_return_level(),
        ):
            assert figure is not None
            plt.close(figure)
