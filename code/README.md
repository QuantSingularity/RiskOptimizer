# RiskOptimizer

Institutional-grade quantitative risk analysis and portfolio management platform.

## Repository Layout

```
RiskOptimizer/
├── backend/          Flask/Celery REST API
├── blockchain/       Smart contracts and Web3 integration
└── quant_ml/         Quantitative ML and risk model services
```

### `backend/`

The Flask API layer. Handles authentication, portfolio and risk endpoints,
Celery task workers, Redis caching, and PostgreSQL persistence.

**Entry point:** `backend/app.py`

### `blockchain/`

Ethereum smart contracts (Solidity), Truffle migration scripts, blockchain
tests, and the Python Web3 integration service.

**Key files:**

- `contracts/` - Solidity source for PortfolioTracker and RiskManagement
- `services/blockchain_service.py` - Python service consumed by the backend
- `web3_integration.py` - standalone Web3 helper / demo script

### `quant_ml/`

Installable Python library (`pip install -e quant_ml`) with a `src/` layout. The
backend reaches it through `backend/src/services/quant_ml_bridge.py`.

| Sub-package     | Purpose                                                                   |
| --------------- | ------------------------------------------------------------------------- |
| `data/`         | Historical price loading and bundled datasets                             |
| `optimization/` | ML, classical and mean-variance portfolio optimizers                      |
| `forecasting/`  | Price forecasting and sentiment analysis                                  |
| `risk/`         | EVT, ML, copula and hybrid risk models, analytics, parallel risk engine   |
| `training/`     | Model training pipeline and CLI                                           |
| `reporting/`    | Report templates, escaped HTML and PDF generation, scheduling and archive |
| `settings.py`   | Paths and constants, overridable through environment variables            |
| `tests/`        | `unit/`, `integration/` and `performance/` suites                         |

### Backend API surface for `quant_ml`

| Route prefix           | Capability                                                                  |
| ---------------------- | --------------------------------------------------------------------------- |
| `/api/v1/optimization` | ML portfolio optimization, frontier, simulation, forecast, sentiment, model |
| `/api/v1/quant`        | EVT, ML, copula and hybrid risk, engine analytics, mean-variance, reports   |
| `/api/v1/tasks`        | Celery task submission and status                                           |
