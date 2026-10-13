import numpy as np
import pytest
from risk.copula import COPULA_TYPES, CopulaMLRiskModel


@pytest.fixture(scope="module", params=COPULA_TYPES)
def model(request, returns_frame):
    return CopulaMLRiskModel(request.param, 20000, seed=1).fit(returns_frame)


class TestCopula:
    def test_fit_state(self, model, returns_frame):
        assert model.trained
        assert list(model.asset_names) == list(returns_frame.columns)
        assert model.correlation_matrix.shape == (3, 3)
        assert np.allclose(np.diag(model.correlation_matrix), 1.0)

    def test_scenarios_preserve_marginals(self, model, returns_frame):
        scenarios = model.generate_scenarios(20000)
        assert scenarios.shape == (20000, 3)
        assert not scenarios.isna().any().any()
        for column in returns_frame:
            assert scenarios[column].mean() == pytest.approx(
                returns_frame[column].mean(), abs=0.0015
            )
            assert scenarios[column].std() == pytest.approx(
                returns_frame[column].std(), rel=0.1
            )

    def test_portfolio_risk_matches_empirical(self, model, returns_frame):
        weights = np.full(3, 1 / 3)
        realised = returns_frame.to_numpy() @ weights
        empirical = -np.quantile(realised, 0.05)
        if model.copula_type in ("gaussian", "t"):
            assert model.calculate_var(weights, 0.95) == pytest.approx(
                empirical, rel=0.2
            )
        assert model.calculate_var(weights, 0.95) > 0

    def test_ordering(self, model):
        weights = [0.5, 0.3, 0.2]
        assert model.calculate_var(weights, 0.95) < model.calculate_var(weights, 0.99)
        assert model.calculate_es(weights, 0.95) >= model.calculate_var(weights, 0.95)

    def test_seeded_reproducibility(self, model):
        weights = [0.4, 0.4, 0.2]
        assert model.calculate_var(weights, 0.95) == model.calculate_var(weights, 0.95)

    def test_metrics_keys_and_dict_weights(self, model, returns_frame):
        metrics = model.calculate_risk_metrics({"A0": 0.5, "A1": 0.5}, [0.9, 0.975])
        assert {
            "mean",
            "std",
            "skewness",
            "kurtosis",
            "var_90",
            "es_90",
            "var_97_5",
            "es_97_5",
        } <= set(metrics)


class TestDependence:
    def test_gaussian_reproduces_correlation(self, returns_frame):
        model = CopulaMLRiskModel("gaussian", 50000, seed=2).fit(returns_frame)
        simulated = model.generate_scenarios().corr().to_numpy()
        empirical = returns_frame.corr().to_numpy()
        assert np.allclose(simulated, empirical, atol=0.1)

    def test_clayton_has_lower_tail_dependence(self, returns_frame):
        model = CopulaMLRiskModel("clayton", 50000, seed=2).fit(returns_frame)
        scenarios = model.generate_scenarios()
        low = scenarios.quantile(0.05)
        joint_low = (
            (scenarios["A0"] <= low["A0"]) & (scenarios["A1"] <= low["A1"])
        ).mean()
        assert joint_low / 0.05 > 0.2

    def test_negative_correlation_does_not_produce_nan(self):
        rng = np.random.default_rng(5)
        x = rng.normal(0, 0.01, 500)
        frame = {"a": x, "b": -x + rng.normal(0, 0.002, 500)}
        for copula in COPULA_TYPES:
            scenarios = (
                CopulaMLRiskModel(copula, 500, seed=1).fit(frame).generate_scenarios()
            )
            assert not scenarios.isna().any().any()

    def test_single_asset(self):
        model = CopulaMLRiskModel("gaussian", 1000, seed=1).fit(
            np.random.default_rng(0).normal(0, 0.01, 200)
        )
        assert model.calculate_var([1.0], 0.95) > 0


class TestErrors:
    def test_untrained(self):
        model = CopulaMLRiskModel()
        for call in (
            lambda: model.generate_scenarios(),
            lambda: model.calculate_var([1.0]),
            lambda: model.calculate_es([1.0]),
        ):
            with pytest.raises(ValueError):
                call()

    @pytest.mark.parametrize(
        "kwargs", [{"copula_type": "bogus"}, {"n_scenarios": 0}, {"n_scenarios": True}]
    )
    def test_constructor(self, kwargs):
        with pytest.raises(ValueError):
            CopulaMLRiskModel(**kwargs)

    def test_bad_weights_and_data(self, returns_frame):
        model = CopulaMLRiskModel(seed=1).fit(returns_frame)
        with pytest.raises(ValueError):
            model.calculate_var([0.5, 0.5])
        with pytest.raises(ValueError):
            model.calculate_var({"nope": 1.0})
        with pytest.raises(ValueError):
            model.calculate_var([1, 0, 0], confidence=1.5)
        with pytest.raises(ValueError):
            CopulaMLRiskModel().fit(returns_frame.head(5))

    def test_plot(self, returns_frame):
        import matplotlib.pyplot as plt

        figure = (
            CopulaMLRiskModel(seed=1)
            .fit(returns_frame)
            .plot_return_distribution([1, 1, 1])
        )
        plt.close(figure)
