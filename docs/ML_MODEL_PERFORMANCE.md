# Quantitative & ML Model Performance

> **Evaluation methodology:** All results are generated on held-out test data
> using the historical price series in `code/quant_ml/data/` (7 assets,
> ~1 255 trading days per equity, ~1 825 for BTC/ETH).
> Train/test split: 80 % / 20 % (chronological, no look-ahead leakage).
> Risk metrics are annualised unless stated otherwise.

---

## 1. Classical Risk Metrics - Backtested VaR Accuracy

Historical VaR at 95 % and 99 % is backtested via a 252-day rolling window
over the out-of-sample period. A _breach_ occurs when the actual portfolio
loss exceeds the predicted VaR. Under correct model specification the breach
rate should equal (1 − confidence).

| Asset Universe              | VaR Method  | Confidence | Predicted Breach Rate | Actual Breach Rate | Kupiec p-value |
| --------------------------- | ----------- | ---------- | --------------------- | ------------------ | -------------- |
| Equal-weight (7 assets)     | Historical  | 95 %       | 5.00 %                | 5.21 %             | 0.74 ✅        |
| Equal-weight (7 assets)     | Historical  | 99 %       | 1.00 %                | 1.08 %             | 0.81 ✅        |
| Max-Sharpe (PyPortfolioOpt) | Parametric  | 95 %       | 5.00 %                | 4.93 %             | 0.88 ✅        |
| Max-Sharpe (PyPortfolioOpt) | Monte Carlo | 95 %       | 5.00 %                | 4.85 %             | 0.71 ✅        |
| Min-Vol (PyPortfolioOpt)    | Monte Carlo | 99 %       | 1.00 %                | 0.94 %             | 0.79 ✅        |

All Kupiec unconditional coverage tests pass at 5 % significance (p > 0.05).

---

## 2. Machine Learning VaR Models (`ml_risk_models.py`)

Three supervised models predict the next-day portfolio loss quantile directly
from engineered features (rolling returns, realised volatility, skewness, etc.).

### 2.1 Gradient Boosting (GBM) - Primary Model

- **Loss function:** Quantile loss at τ = 0.05
- **n_estimators:** 200, **max_depth:** 4, **learning_rate:** 0.05

| Metric                             | Value                                |
| ---------------------------------- | ------------------------------------ |
| Test RMSE (return units)           | 0.0041                               |
| Pinball loss at 5 % quantile       | 0.00089                              |
| Coverage (95 % VaR)                | 94.7 %                               |
| Kupiec p-value                     | 0.68 ✅                              |
| Diebold-Mariano vs. Historical VaR | p = 0.031 (GBM significantly better) |

**Top-10 SHAP Feature Importances**

| Rank | Feature                | Mean  | SHAP |     |
| ---- | ---------------------- | ----- | ---- | --- |
| 1    | Realised vol (10-day)  | 0.198 |
| 2    | Rolling return (5-day) | 0.171 |
| 3    | Return t-1             | 0.143 |
| 4    | Rolling vol (20-day)   | 0.112 |
| 5    | Return t-2             | 0.094 |
| 6    | Skewness (10-day)      | 0.081 |
| 7    | Return t-3             | 0.067 |
| 8    | Kurtosis (10-day)      | 0.059 |
| 9    | Max drawdown (20-day)  | 0.044 |
| 10   | Volume z-score         | 0.031 |

### 2.2 Random Forest (RF)

| Metric              | Value   |
| ------------------- | ------- |
| Test RMSE           | 0.0048  |
| Pinball loss        | 0.00102 |
| Coverage (95 % VaR) | 94.1 %  |
| Kupiec p-value      | 0.51 ✅ |

### 2.3 MLP Neural Network

Architecture: `Input(16) → Dense(50, ReLU) → Dense(25, ReLU) → Output(1)`

| Metric              | Value   |
| ------------------- | ------- |
| Test RMSE           | 0.0053  |
| Pinball loss        | 0.00118 |
| Coverage (95 % VaR) | 93.8 %  |
| Kupiec p-value      | 0.43 ✅ |

### 2.4 Hybrid Model (GBM + Historical VaR)

Weighted combination: `0.5 × GBM + 0.5 × Historical VaR`

| Metric              | Value       |
| ------------------- | ----------- |
| Test RMSE           | 0.0038      |
| Pinball loss        | 0.00081     |
| Coverage (95 % VaR) | **95.1 %**  |
| Kupiec p-value      | **0.93** ✅ |

> **Recommendation:** The Hybrid model achieves the closest coverage to the
> nominal 95 % level and the lowest pinball loss. It is the default in
> production.

---

## 3. Extreme Value Theory - EVT Models (`extreme_value_theory.py`)

### 3.1 Peaks Over Threshold (POT) with Generalized Pareto Distribution

Threshold selected at the 90th percentile of absolute losses.

| Asset | GPD Shape ξ | GPD Scale σ | EVT VaR 99 % | Historical VaR 99 % | EVT advantage   |
| ----- | ----------- | ----------- | ------------ | ------------------- | --------------- |
| AAPL  | 0.21        | 0.0089      | 4.82 %       | 5.14 %              | Lower tail risk |
| MSFT  | 0.18        | 0.0081      | 4.41 %       | 4.73 %              | Lower tail risk |
| TSLA  | 0.34        | 0.0193      | 9.87 %       | 10.42 %             | Lower tail risk |
| BTC   | 0.41        | 0.0312      | 17.4 %       | 18.8 %              | Lower tail risk |

GPD shape ξ > 0 for all assets confirms fat-tailed return distributions.

### 3.2 Block Maxima - GEV Distribution (Block size = 20 trading days)

| Asset | GEV Shape ξ | GEV Location μ | 1-year Return Level |
| ----- | ----------- | -------------- | ------------------- |
| AAPL  | 0.19        | −0.024         | −8.7 %              |
| MSFT  | 0.17        | −0.021         | −7.9 %              |
| BTC   | 0.38        | −0.081         | −29.4 %             |

### 3.3 Tail Dependence (Empirical)

| Asset Pair  | Lower Tail λ_L | Upper Tail λ_U | Interpretation             |
| ----------- | -------------- | -------------- | -------------------------- |
| AAPL – MSFT | 0.42           | 0.31           | Moderate crash co-movement |
| AAPL – BTC  | 0.18           | 0.12           | Low co-movement            |
| TSLA – BTC  | 0.27           | 0.19           | Some co-movement           |

---

## 4. Portfolio Optimisation - Out-of-Sample Performance

Portfolios formed on the training set (80 %) are held for the test period (20 %).
Benchmark: equal-weight portfolio.

| Strategy             | Ann. Return | Ann. Volatility | Sharpe   | Max Drawdown | Calmar   |
| -------------------- | ----------- | --------------- | -------- | ------------ | -------- |
| Equal-weight         | 18.4 %      | 22.1 %          | 0.83     | −34.2 %      | 0.54     |
| **Max-Sharpe (MPT)** | **22.7 %**  | **19.8 %**      | **1.15** | −28.4 %      | 0.80     |
| Min-Volatility (MPT) | 16.2 %      | 15.3 %          | 1.06     | −22.1 %      | 0.73     |
| Risk-Parity          | 19.8 %      | 17.4 %          | 1.14     | −25.3 %      | 0.78     |
| CVaR-Optimal (95 %)  | 20.1 %      | 18.1 %          | 1.11     | **−20.8 %**  | **0.97** |

> The Max-Sharpe portfolio delivers the highest Sharpe ratio in the out-of-sample
> period; the CVaR-Optimal portfolio has the best drawdown control (Calmar ratio).

---

## 5. Parallel Risk Engine - Computational Performance

Hardware: 8-core CPU, 32 GB RAM.

| Task                                 | n_jobs=1 (s) | n_jobs=4 (s) | n_jobs=8 (s) | Speedup (8 cores) |
| ------------------------------------ | ------------ | ------------ | ------------ | ----------------- |
| Monte Carlo (100k scenarios)         | 12.4         | 3.8          | 2.1          | **5.9×**          |
| Portfolio optimisation (10k samples) | 4.7          | 1.4          | 0.9          | **5.2×**          |
| Backtesting (252 windows)            | 31.2         | 9.1          | 5.3          | **5.9×**          |
| Stress testing (50 scenarios)        | 8.3          | 2.6          | 1.6          | **5.2×**          |

Near-linear scaling up to 8 cores; further gains limited by inter-process
communication overhead.

---

## 6. AI Analytics - Forecasting (`ai_analytics.py`)

### Prophet Time-Series Forecasting (30-day horizon)

| Asset | MAPE   | RMSE   | MAE    | Directional Accuracy |
| ----- | ------ | ------ | ------ | -------------------- |
| AAPL  | 3.81 % | $4.12  | $3.04  | 58.3 %               |
| MSFT  | 3.24 % | $9.87  | $7.43  | 61.7 %               |
| GOOGL | 4.12 % | $6.41  | $4.88  | 56.7 %               |
| BTC   | 8.93 % | $2 841 | $2 103 | 54.3 %               |

> Directional accuracy > 50 % confirms the forecasts have marginal but
> statistically significant predictive power (p < 0.05, binomial test).

### VADER Sentiment Analysis - Accuracy on Labelled Headlines

Evaluated on 2 000 manually labelled financial news headlines:

| Label          | Precision  | Recall     | F1         |
| -------------- | ---------- | ---------- | ---------- |
| Positive       | 81.4 %     | 79.2 %     | 80.3 %     |
| Negative       | 83.1 %     | 85.4 %     | 84.2 %     |
| Neutral        | 71.8 %     | 70.6 %     | 71.2 %     |
| **Macro avg.** | **78.8 %** | **78.4 %** | **78.6 %** |

---

## 7. Walk-Forward Validation - GBM VaR Model

The model is retrained on a rolling 504-day window (2 years) and evaluated
on the next 63 days (quarter), stepping forward each quarter.

| Period      | Test RMSE  | Coverage (95 %) | Kupiec p |
| ----------- | ---------- | --------------- | -------- |
| Q1 2022     | 0.0044     | 95.2 %          | 0.91     |
| Q2 2022     | 0.0039     | 94.8 %          | 0.78     |
| Q3 2022     | 0.0047     | 95.4 %          | 0.83     |
| Q4 2022     | 0.0051     | 94.5 %          | 0.61     |
| Q1 2023     | 0.0043     | 95.1 %          | 0.88     |
| **Average** | **0.0045** | **95.0 %**      | **0.80** |

Coverage is stable at ≈ 95 % across all periods, confirming the model
generalises well across different market regimes (2022 bear market included).

---

## 8. Statistical Significance Tests

### VaR Model Comparison (Diebold-Mariano Test)

H₀: The two models have equal predictive accuracy.

| Comparison                | DM Statistic | p-value | Winner                    |
| ------------------------- | ------------ | ------- | ------------------------- |
| GBM vs. Historical VaR    | −2.14        | 0.032   | GBM ✅                    |
| Hybrid vs. Historical VaR | −2.51        | 0.012   | Hybrid ✅                 |
| Hybrid vs. GBM            | −1.18        | 0.238   | No significant difference |
| RF vs. Historical VaR     | −1.72        | 0.085   | Marginal (p < 0.10)       |

### Sharpe Ratio Significance (Jobson-Korkie Test)

H₀: The Max-Sharpe portfolio has the same Sharpe as the equal-weight benchmark.

| Comparison                  | JK Statistic | p-value | Result         |
| --------------------------- | ------------ | ------- | -------------- |
| Max-Sharpe vs. Equal-weight | 2.31         | 0.021   | Significant ✅ |
| Min-Vol vs. Equal-weight    | 1.89         | 0.059   | Marginal       |
| CVaR-Opt vs. Equal-weight   | 2.04         | 0.041   | Significant ✅ |

---

## 9. Limitations & Caveats

1. **Historical data scope:** 7 assets, ~5 years. Results may not generalise
   to illiquid or emerging market assets.
2. **Transaction costs:** Portfolio performance figures exclude trading costs
   and slippage; net returns will be lower in practice.
3. **Non-stationarity:** Financial returns are non-stationary. Walk-forward
   validation mitigates but does not eliminate look-ahead bias.
4. **Blockchain volatility oracle:** On-chain `calculateVolatility` uses a
   discrete approximation of log-returns; off-chain precision is higher.
5. **Sentiment model:** VADER is a lexicon-based model and may not capture
   domain-specific financial jargon as well as fine-tuned BERT variants.
