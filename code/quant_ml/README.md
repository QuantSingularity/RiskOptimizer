# quant_ml

Quantitative library behind the RiskOptimizer backend.

## Layout

```
quant_ml/
  pyproject.toml
  requirements.txt
  requirements-dev.txt
  src/quant_ml/
    settings.py        paths and shared constants (environment overridable)
    data/              historical price loading and bundled datasets
    optimization/      portfolio optimizers (ML, classical, mean-variance)
    forecasting/       price forecasting and sentiment analysis
    risk/              EVT, ML, copula and hybrid risk models, analytics, parallel engine
    training/          model training pipeline and CLI
    reporting/         report templates, generation, scheduling and archive
  tests/
    unit/              fast isolated tests
    integration/       cross-module tests
    performance/       statistical calibration checks
```

## Install

```
pip install -e ".[dev]"
```

## Test

```
pytest
pytest -m "not performance"
```

## Configuration

| Variable                | Purpose                                              |
| ----------------------- | ---------------------------------------------------- |
| `QUANT_ML_DATA_DIR`     | directory containing `<SYMBOL>_historical.csv` files |
| `QUANT_ML_ARTIFACT_DIR` | trained model and report output directory            |
| `QUANT_ML_REPORT_DIR`   | report output directory                              |
| `MODEL_PATH`            | explicit path of the portfolio optimizer model file  |

## Training

```
quant-ml-train --visualize
python -m quant_ml.training.cli --symbols AAPL MSFT BTC_USD
```
