# Quant Models and Optimization Examples

Examples for the models in `code/quant_ml`. Every Python snippet on this page runs against the bundled datasets. Install the library first:

```bash
pip install -e "code/quant_ml[dev]"
```

## Example 1: Train and use the portfolio optimizer

Train from the command line (also runs a hold-out evaluation):

```bash
./scripts/model_training.sh -m optimization -s AAPL MSFT GOOGL BTC_USD --visualize
```

Or from Python:

```python
from quant_ml.data import load_close_prices
from quant_ml.optimization import AdvancedPortfolioOptimizer
from quant_ml.training.trainer import train_and_save

symbols = ["AAPL", "MSFT", "GOOGL", "BTC_USD"]
model, report, path = train_and_save("optimizer.joblib", symbols=symbols)
print("Hold-out metrics:", report["prediction_metrics"])

prices = load_close_prices(symbols)
loaded = AdvancedPortfolioOptimizer.load_model(path)
weights, metrics = loaded.optimize_portfolio(prices, max_weight=0.4, method="max_sharpe")

for asset, weight in weights.items():
    print(f"{asset}: {weight:.2%}")
print(metrics)
```

## Example 2: Optimization methods

```python
from quant_ml.data import load_close_prices
from quant_ml.optimization import optimize_weights

returns = load_close_prices(["AAPL", "MSFT", "GOOGL", "AMZN"]).pct_change().dropna()

for method in ("mean_variance", "minimum_variance", "risk_parity"):
    result = optimize_weights(returns, method, {"max_weight_per_asset": 0.5})
    print(method, {k: round(v, 3) for k, v in result["weights"].items()})

views = [{"assets": {"AAPL": 1.0}, "return": 0.30, "confidence": 0.7}]
blended = optimize_weights(returns, "black_litterman", {"views": views})
print("black_litterman", {k: round(v, 3) for k, v in blended["weights"].items()})
```

Bounds are enforced, not just reported, and `constraints_satisfied` in the result confirms them.

## Example 3: Price forecast with validation evidence

```python
from quant_ml.forecasting import forecast_prices

result = forecast_prices("AAPL", periods=10)

print("Selected model:", result["model"], "| beats naive:", result["beats_naive"])
print("Validation:", result["validation"]["scores"])
for row in result["forecast"][:3]:
    print(row["date"], round(row["yhat"], 2), round(row["yhat_lower"], 2), round(row["yhat_upper"], 2))
```

`model="auto"` validates naive, drift and damped ETS over rolling windows and only leaves the naive forecast when another model wins consistently. `model="prophet"` is available on request and returns a warning when it does not beat the baseline.

## Example 4: Sentiment

```python
from quant_ml.forecasting import analyze_sentiment, summarize_sentiment

frame = analyze_sentiment(
    [
        "Shares surge in a record rally after strong earnings",
        "Company files for bankruptcy as sales plunge",
    ]
)
print(frame[["compound", "sentiment"]])
print(summarize_sentiment(frame))
```

## Example 5: Risk models on one portfolio

```python
import numpy as np

from quant_ml.data import load_close_prices
from quant_ml.risk import CopulaMLRiskModel, ExtremeValueRisk, HybridRiskModel, MLRiskModel

returns = load_close_prices(["AAPL", "MSFT", "TSLA", "BTC_USD"]).pct_change().dropna()
weights = np.array([0.3, 0.3, 0.2, 0.2])
portfolio = returns.to_numpy() @ weights

evt = ExtremeValueRisk(seed=0).fit_pot(portfolio, threshold_quantile=0.05)
print("EVT 99% VaR/ES:", round(evt.calculate_var(0.99), 4), round(evt.calculate_es(0.99), 4))

copula = CopulaMLRiskModel("t", 20000, seed=1).fit(returns)
print("Copula metrics:", {k: round(v, 4) for k, v in copula.calculate_risk_metrics(weights).items()})

ml = MLRiskModel("gbm").fit(returns, weights=weights)
print("ML next-day 95% VaR:", round(ml.forecast_var(returns, 0.95), 4))

hybrid = HybridRiskModel(0.5, "rf", seed=1).fit(returns, weights=weights)
print("Hybrid:", {k: round(v, 4) for k, v in hybrid.calculate_risk_metrics(returns, weights).items()})
```

All VaR and expected shortfall figures are one period losses as positive fractions of portfolio value.

## Example 6: Backtest the models

```python
from quant_ml.data import load_close_prices
from quant_ml.risk import ParallelRiskEngine

returns = load_close_prices(["AAPL", "MSFT", "TSLA", "BTC_USD"]).pct_change().dropna()
engine = ParallelRiskEngine(n_jobs=1, seed=1)

result = engine.parallel_backtest(returns, ["historical", "evt", "parametric"], 0.95)
for model, stats in result["summary"].items():
    print(model, f"breach rate {stats['breach_rate']:.3f}", f"Kupiec p {stats['kupiec_pvalue']:.2f}")
```

A breach rate close to 5% and a Kupiec p-value above 0.01 mean the 95% VaR is well calibrated. The same checks run for all models with `./scripts/model_training.sh --evaluate-only --strict`.

## Example 7: Generate a PDF risk report

```python
import pandas as pd

from quant_ml.reporting import ReportGenerator, ReportTemplate

template = ReportTemplate("Weekly Risk Report", author="Risk Desk")
template.add_section("Summary", "Tail risk is **stable** this week.", "text")
template.add_section("Metrics", {"data_key": "metrics", "options": {"show_index": False}}, "table")

data = {"metrics": pd.DataFrame({"Model": ["historical", "evt"], "VaR 99%": [0.052, 0.056]})}
print("written:", ReportGenerator(template).generate_pdf("weekly_risk.pdf", data))
```

Section text and table cells are escaped, so untrusted content cannot inject markup.

### Email delivery

Scheduled and task generated reports are emailed when SMTP is configured through environment variables:

| Variable                                       | Purpose                                         |
| :--------------------------------------------- | :---------------------------------------------- |
| `QUANT_ML_SMTP_HOST`, `QUANT_ML_SMTP_SENDER`   | Required to enable delivery                     |
| `QUANT_ML_SMTP_PORT`                           | Default 587 (465 with `QUANT_ML_SMTP_SSL=true`) |
| `QUANT_ML_SMTP_USER`, `QUANT_ML_SMTP_PASSWORD` | Optional authentication                         |
| `QUANT_ML_SMTP_TLS`                            | STARTTLS, default `true`                        |

Without them the result reports `delivered: false` with the reason.

## Example 8: The same models through the API

```python
import requests

base = "http://localhost:8080/api/v1"
headers = {"Authorization": "Bearer <token>"}

optimized = requests.post(
    f"{base}/optimization/optimize",
    json={"symbols": ["AAPL", "MSFT", "GOOGL"], "method": "max_sharpe", "max_weight": 0.5},
    headers=headers,
).json()["data"]

risk = requests.post(
    f"{base}/quant/risk/evt",
    json={"symbols": ["AAPL", "MSFT"], "weights": {"AAPL": 0.6, "MSFT": 0.4}},
    headers=headers,
).json()["data"]

report = requests.post(
    f"{base}/quant/reports/risk",
    json={"symbols": ["AAPL", "MSFT"], "format": "pdf", "recipients": ["desk@example.com"]},
    headers=headers,
).json()["data"]
```
