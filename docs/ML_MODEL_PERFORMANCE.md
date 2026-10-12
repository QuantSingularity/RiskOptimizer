# Quantitative and ML Model Performance

> Every number on this page is produced by `quant-ml-benchmark` (`code/quant_ml/src/quant_ml/training/benchmark.py`) and can be reproduced with the commands in the last section. Nothing here is hand entered.

## 1. Data and method

- **Data:** 7 bundled assets (AAPL, AMZN, BTC_USD, ETH_USD, GOOGL, MSFT, TSLA), 1,254 aligned daily returns from 2020-11-16 to 2025-11-13. Prices are inner joined, so no weekend or holiday rows are fabricated for equities.
- **Portfolio:** equal weight across all assets unless stated.
- **Convention:** VaR and expected shortfall are one period losses expressed as positive fractions of portfolio value.
- **Machine:** a single CPU core, so engine timings are single job figures.

## 2. VaR backtests

A rolling 252 day window estimates the 95% VaR, which is then tested on the following days. Every out of sample day is tested (1,002 days). The Kupiec test checks that the breach rate matches the expected 5%; a p-value above 0.01 passes.

| Model      | Breaches | Test days | Breach rate | Breach ratio | Kupiec p-value | Result |
| :--------- | -------: | --------: | ----------: | -----------: | -------------: | :----- |
| parametric |       54 |     1,002 |       5.39% |         1.08 |           0.58 | pass   |
| historical |       49 |     1,002 |       4.89% |         0.98 |           0.87 | pass   |
| evt        |       51 |     1,002 |       5.09% |         1.02 |           0.90 | pass   |

## 3. ML risk models

Each model is trained on the first 70% of history and its 95% VaR predictions are scored on the remaining 30%. Coverage is the share of days on which the realised loss stayed within the predicted VaR; the target is 95%.

| Model | Out of sample coverage | Target | Within tolerance (6 points) |
| :---- | ---------------------: | -----: | :-------------------------- |
| gbm   |                  95.0% |    95% | yes                         |
| rf    |                  96.8% |    95% | yes                         |
| nn    |                  93.1% |    95% | yes                         |

`gbm` uses quantile loss and a calibrated ladder of quantile models for expected shortfall. `rf` and `nn` predict the conditional mean and add the empirical residual tail.

## 4. Extreme value theory accuracy

Peaks over threshold VaR is compared with the exact quantiles of Student t samples with known tails (150,000 samples, threshold at the 5% tail).

| Degrees of freedom | Confidence | True VaR | Estimated VaR | Relative error |
| -----------------: | ---------: | -------: | ------------: | -------------: |
|                  3 |      99.0% |   0.0454 |        0.0455 |          +0.3% |
|                  3 |      99.5% |   0.0584 |        0.0584 |          +0.1% |
|                  4 |      99.0% |   0.0375 |        0.0375 |          +0.2% |
|                  4 |      99.5% |   0.0460 |        0.0462 |          +0.4% |
|                  6 |      99.0% |   0.0314 |        0.0315 |          +0.2% |
|                  6 |      99.5% |   0.0371 |        0.0373 |          +0.7% |

## 5. Copula models against the empirical portfolio

Scenarios are simulated from each fitted copula (empirical marginals) and the equal weight portfolio is measured against its own historical distribution.

| Source          | Daily std | 95% VaR | 99% VaR |
| :-------------- | --------: | ------: | ------: |
| Empirical       |    0.0207 |  0.0329 |  0.0559 |
| gaussian copula |    0.0206 |  0.0312 |  0.0512 |
| t copula        |    0.0208 |  0.0305 |  0.0535 |
| clayton copula  |    0.0217 |  0.0364 |  0.0670 |
| gumbel copula   |    0.0223 |  0.0297 |  0.0454 |

The Gaussian and t copulas track the empirical tail closely. The one parameter Clayton and Gumbel copulas impose a single dependence structure on all assets, so they over or under state the tail for this mixed equity and crypto portfolio.

## 6. Portfolio optimizer hold out

The ML return model is trained on the first 80% and evaluated on the last 230 days.

| Metric                                   |    Value |
| :--------------------------------------- | -------: |
| Next day return prediction R squared     |    0.033 |
| Next day return prediction MSE           | 0.000419 |
| Optimized portfolio expected return      |    0.148 |
| Optimized portfolio volatility           |    0.229 |
| Optimized portfolio Sharpe ratio         |    0.558 |
| 95% one year Monte Carlo VaR (on 10,000) |    1,262 |
| 99% one year Monte Carlo VaR (on 10,000) |    2,599 |

An R squared near 0.03 shows that next day returns are very hard to predict. The optimizer blends the model's estimate with a prior (controlled by risk tolerance) rather than trusting it, which is why the weights remain diversified.

## 7. Price forecasting

`forecast_prices(model="auto")` validates candidate models over 24 rolling windows at a 10 day horizon and keeps the naive forecast unless another model wins by at least 1% on average and in at least 65% of windows. Scores are mean absolute percentage errors.

| Asset   | Selected | Naive | Drift | Damped ETS | Beats naive |
| :------ | :------- | ----: | ----: | ---------: | :---------- |
| AAPL    | naive    | 3.75% | 3.79% |      3.75% | no          |
| AMZN    | naive    | 3.61% | 3.64% |      3.61% | no          |
| BTC_USD | naive    | 3.20% | 3.13% |      3.20% | no          |
| ETH_USD | naive    | 6.23% | 6.77% |      6.34% | no          |
| GOOGL   | naive    | 3.26% | 3.23% |      3.23% | no          |
| MSFT    | naive    | 2.67% | 2.71% |      2.68% | no          |
| TSLA    | naive    | 6.53% | 6.74% |      6.45% | no          |

Prophet is available on request (`model="prophet"`) but is not considered by `auto`. Over 12 rolling windows it did not consistently beat the naive baseline:

| Asset   | Skill vs naive | Win rate vs naive |
| :------ | -------------: | ----------------: |
| AAPL    |          +9.0% |               50% |
| AMZN    |          -6.5% |               42% |
| BTC_USD |         -58.9% |               25% |
| ETH_USD |         -48.6% |               33% |
| GOOGL   |         -26.3% |               33% |
| MSFT    |         -58.8% |               17% |
| TSLA    |         -35.4% |               42% |

Forecast intervals use volatility scaled bands. In walk forward tests of the 95% band, coverage was between 91% and 98%.

## 8. Parallel risk engine timing

| Jobs | Monte Carlo                | Portfolio search           | Rolling backtest |
| ---: | :------------------------- | :------------------------- | ---------------: |
|    1 | 100,000 scenarios in 0.28s | 10,000 portfolios in 0.13s |            0.94s |

Work is split into seeded batches, so results are identical for any number of jobs.

## 9. Limitations

1. **Scope of data:** 7 assets over about five years. Results may not generalise to illiquid assets or other regimes.
2. **Transaction costs:** performance figures exclude trading costs and slippage.
3. **Non stationarity:** returns are non stationary; rolling validation reduces but does not remove this.
4. **Forecasting:** with these assets no candidate consistently beats a naive random walk; the forecaster reports that rather than hiding it.
5. **Sentiment:** the VADER analyzer is lexicon based and is not benchmarked on this page.
6. **Single machine:** timings come from a one core machine; multi core speedups are not measured here.

## 10. Reproduce

```bash
pip install -e "code/quant_ml[dev]"
quant-ml-benchmark --output benchmark.json
./scripts/model_training.sh --evaluate-only --strict
```
