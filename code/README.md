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

All Python quantitative and ML services.

| Sub-package | Purpose |
|---|---|
| `risk_engine/` | Parallel Monte Carlo, backtesting, sensitivity analysis |
| `risk_models/` | EVT, ML risk models, portfolio optimisation, GARCH |
| `ai_models/` | Prophet forecasting, sentiment analysis, RL optimiser |
| `reporting/` | HTML/PDF report generation, scheduling, archiving |
| `data/` | Historical OHLCV CSV files |
| `tests/` | Comprehensive test suite |

## Docker (full stack)

```bash
docker-compose up --build
```
