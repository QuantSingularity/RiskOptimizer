import numpy as np
import pytest
from risk.copula import CopulaMLRiskModel
from risk.engine import ParallelRiskEngine
from risk.evt import ExtremeValueRisk
from risk.ml import MLRiskModel
from scipy import stats

pytestmark = pytest.mark.performance


@pytest.mark.parametrize("df,seed", [(3, 1), (4, 2), (6, 3)])
def test_evt_quantiles_track_student_t_truth(df, seed):
    data = stats.t.rvs(df, size=150_000, random_state=seed) * 0.01
    model = ExtremeValueRisk().fit_pot(data, threshold_quantile=0.05)
    for confidence in (0.99, 0.995):
        truth = -stats.t.ppf(1 - confidence, df) * 0.01
        assert model.calculate_var(confidence) == pytest.approx(truth, rel=0.1)
    assert model.pot_params["shape"] == pytest.approx(1.0 / df, abs=0.12)


@pytest.mark.parametrize("model_type", ["gbm", "rf", "nn"])
def test_ml_models_are_calibrated_out_of_sample(model_type, real_returns):
    split = int(len(real_returns) * 0.7)
    model = MLRiskModel(model_type).fit(real_returns.iloc[:split])
    var = model.predict_var(real_returns, 0.95)
    realised = -(
        real_returns.to_numpy()
        @ np.full(real_returns.shape[1], 1 / real_returns.shape[1])
    )[10:]
    test = slice(split - 10, len(realised))
    coverage = np.mean(realised[test] <= var[: len(realised)][test])
    assert 0.90 <= coverage <= 0.995


def test_gbm_pinball_loss_beats_unconditional_quantile(real_returns):
    split = int(len(real_returns) * 0.7)
    model = MLRiskModel("gbm").fit(real_returns.iloc[:split])
    var = model.predict_var(real_returns, 0.95)
    realised = -(
        real_returns.to_numpy()
        @ np.full(real_returns.shape[1], 1 / real_returns.shape[1])
    )[10:]
    test = slice(split - 10, len(realised))
    level = 0.95

    def pinball(actual, predicted):
        errors = actual - predicted
        return np.mean(np.where(errors >= 0, level * errors, (level - 1) * errors))

    unconditional = np.quantile(realised[: split - 10], level)
    assert (
        pinball(realised[test], var[: len(realised)][test])
        < pinball(realised[test], unconditional) * 1.1
    )


@pytest.mark.parametrize("copula", ["gaussian", "t"])
def test_elliptical_copulas_reproduce_portfolio_tail(copula, real_returns):
    weights = np.full(real_returns.shape[1], 1 / real_returns.shape[1])
    series = real_returns.to_numpy() @ weights
    model = CopulaMLRiskModel(copula, 100_000, seed=1).fit(real_returns)
    assert model.calculate_var(weights, 0.95) == pytest.approx(
        -np.quantile(series, 0.05), rel=0.15
    )
    assert model.calculate_risk_metrics(weights)["std"] == pytest.approx(
        series.std(), rel=0.08
    )


def test_backtests_pass_kupiec_on_real_portfolio(real_returns):
    engine = ParallelRiskEngine(n_jobs=1)
    result = engine.parallel_backtest(real_returns, ["historical", "evt"], 0.95)
    for summary in result["summary"].values():
        assert summary["kupiec_pvalue"] > 0.01
