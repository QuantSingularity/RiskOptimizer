# Feature Matrix

Comprehensive feature overview for RiskOptimizer v1.0.0.

## Table of Contents

- [Core Features](#core-features)
- [Risk Analysis Features](#risk-analysis-features)
- [Portfolio Management Features](#portfolio-management-features)
- [AI/ML Features](#aiml-features)
- [Blockchain Features](#blockchain-features)
- [Infrastructure Features](#infrastructure-features)

## Core Features

| Feature            | Short description                      | Module / File                                         | CLI flag / API        | Example (path)          | Notes                          |
| ------------------ | -------------------------------------- | ----------------------------------------------------- | --------------------- | ----------------------- | ------------------------------ |
| **REST API**       | Flask-based REST API with Swagger docs | `code/backend/app.py`                                 | API endpoints         | `/api/v1/*`             | JWT authentication             |
| **Web Dashboard**  | React-based web interface              | `web-frontend/`                                       | `npm start`           | `http://localhost:3000` | Responsive design              |
| **Mobile App**     | React Native mobile app                | `mobile-frontend/`                                    | `npm run android/ios` | -                       | iOS & Android support          |
| **Authentication** | JWT-based auth with refresh tokens     | `code/backend/src/api/controllers/auth_controller.py` | `/api/v1/auth/*`      | [USAGE.md](USAGE.md)    | Secure token management        |
| **Database**       | SQLite/PostgreSQL support              | `code/backend/src/infrastructure/database/`           | ENV: `DB_USE_SQLITE`  | -                       | Connection pooling             |
| **Caching**        | Redis-based caching layer              | `code/backend/src/infrastructure/cache/`              | ENV: `REDIS_HOST`     | -                       | Optional, improves performance |

## Risk Analysis Features

| Feature                 | Short description                       | Module / File                                            | CLI flag / API                    | Example (path)                                                 | Notes                                |
| ----------------------- | --------------------------------------- | -------------------------------------------------------- | --------------------------------- | -------------------------------------------------------------- | ------------------------------------ |
| **Value at Risk (VaR)** | Historical & parametric VaR calculation | `code/backend/src/domain/services/risk_service.py`       | `/api/v1/risk/var`                | [examples/BASIC_USAGE.md](examples/BASIC_USAGE.md)             | 95%, 99% confidence levels           |
| **Conditional VaR**     | Expected shortfall calculation          | `code/backend/src/domain/services/risk_service.py`       | `/api/v1/risk/cvar`               | [examples/BASIC_USAGE.md](examples/BASIC_USAGE.md)             | Also known as Expected Shortfall     |
| **Sharpe Ratio**        | Risk-adjusted return metric             | `code/backend/src/domain/services/risk_service.py`       | `/api/v1/risk/sharpe-ratio`       | [examples/BASIC_USAGE.md](examples/BASIC_USAGE.md)             | Configurable risk-free rate          |
| **Maximum Drawdown**    | Peak-to-trough decline calculation      | `code/backend/src/domain/services/risk_service.py`       | `/api/v1/risk/max-drawdown`       | [examples/BASIC_USAGE.md](examples/BASIC_USAGE.md)             | Recovery period tracking             |
| **Correlation Matrix**  | Asset correlation analysis              | `code/quant_ml/src/quant_ml/risk/analysis.py`            | `/api/v1/quant/risk/analysis`     | [examples/BASIC_USAGE.md](examples/BASIC_USAGE.md)             | Pandas-based calculation             |
| **Monte Carlo VaR**     | Simulation-based VaR                    | `code/quant_ml/src/quant_ml/risk/analysis.py`            | `/api/v1/quant/risk/analysis`     | [examples/BASIC_USAGE.md](examples/BASIC_USAGE.md)             | Seeded, reproducible                 |
| **GARCH Volatility**    | Time-series volatility forecasting      | `code/quant_ml/src/quant_ml/risk/analysis.py`            | `/api/v1/quant/risk/analysis`     | [examples/ADVANCED_FEATURES.md](examples/ADVANCED_FEATURES.md) | GARCH(1,1) model, annualized         |
| **Stress Testing**      | Extreme scenario analysis               | `code/quant_ml/src/quant_ml/risk/stress.py`, `engine.py` | `/api/v1/quant/risk/stress-test`  | [examples/ADVANCED_FEATURES.md](examples/ADVANCED_FEATURES.md) | Asset class and volatility scenarios |
| **Efficient Frontier**  | Optimal portfolio combinations          | `code/backend/src/domain/services/risk_service.py`       | `/api/v1/risk/efficient-frontier` | [examples/ADVANCED_FEATURES.md](examples/ADVANCED_FEATURES.md) | MPT-based optimization               |
| **Risk Metrics Bundle** | Comprehensive risk dashboard            | `code/backend/src/domain/services/risk_service.py`       | `/api/v1/risk/metrics`            | [examples/BASIC_USAGE.md](examples/BASIC_USAGE.md)             | All metrics in one call              |

## Portfolio Management Features

| Feature                  | Short description           | Module / File                                                | CLI flag / API                     | Example (path)                                                 | Notes                     |
| ------------------------ | --------------------------- | ------------------------------------------------------------ | ---------------------------------- | -------------------------------------------------------------- | ------------------------- |
| **Create Portfolio**     | Create and save portfolios  | `code/backend/src/api/controllers/portfolio_controller.py`   | `/api/v1/portfolio`                | [USAGE.md](USAGE.md)                                           | Multi-asset support       |
| **Update Portfolio**     | Modify existing portfolios  | `code/backend/src/api/controllers/portfolio_controller.py`   | `/api/v1/portfolio/{id}`           | [USAGE.md](USAGE.md)                                           | Versioning support        |
| **Delete Portfolio**     | Remove portfolios           | `code/backend/src/api/controllers/portfolio_controller.py`   | `/api/v1/portfolio/{id}`           | [USAGE.md](USAGE.md)                                           | Soft delete               |
| **List Portfolios**      | Get user portfolios         | `code/backend/src/api/controllers/portfolio_controller.py`   | `/api/v1/portfolio/user/{id}`      | [USAGE.md](USAGE.md)                                           | Pagination support        |
| **Blockchain Sync**      | Sync with blockchain ledger | `code/backend/src/api/controllers/portfolio_controller.py`   | `/api/v1/portfolio/address/{addr}` | [examples/ADVANCED_FEATURES.md](examples/ADVANCED_FEATURES.md) | Web3 integration          |
| **Asset Allocation**     | Visual allocation breakdown | `web-frontend/src/components/dashboard/AssetAllocation.jsx`  | Web UI                             | -                                                              | Interactive charts        |
| **Performance Tracking** | Historical performance      | `web-frontend/src/components/dashboard/PerformanceChart.jsx` | Web UI                             | -                                                              | Time-series visualization |

## AI/ML Features

| Feature                    | Short description                               | Module / File                                            | CLI flag / API                                | Example (path)                                                 | Notes                               |
| -------------------------- | ----------------------------------------------- | -------------------------------------------------------- | --------------------------------------------- | -------------------------------------------------------------- | ----------------------------------- |
| **Portfolio Optimization** | ML, mean-variance, risk parity, Black-Litterman | `code/quant_ml/src/quant_ml/optimization/`               | `/api/v1/optimization/optimize`               | [examples/AI_OPTIMIZATION.md](examples/AI_OPTIMIZATION.md)     | scikit-learn, SciPy, PyPortfolioOpt |
| **Rebalancing Plan**       | Trades, costs and residual tracking error       | `code/quant_ml/src/quant_ml/optimization/rebalancing.py` | Celery task `rebalance_portfolio`             | [examples/AI_OPTIMIZATION.md](examples/AI_OPTIMIZATION.md)     | Respects minimum trade size         |
| **ML Risk Prediction**     | Quantile and residual based VaR and ES          | `code/quant_ml/src/quant_ml/risk/ml.py`                  | `/api/v1/quant/risk/ml`                       | [examples/AI_OPTIMIZATION.md](examples/AI_OPTIMIZATION.md)     | GBM, random forest, MLP             |
| **Copula Risk**            | Gaussian, t, Clayton and Gumbel dependence      | `code/quant_ml/src/quant_ml/risk/copula.py`              | `/api/v1/quant/risk/copula`                   | [examples/AI_OPTIMIZATION.md](examples/AI_OPTIMIZATION.md)     | Empirical marginals                 |
| **Hybrid Risk**            | Blend of copula and ML estimates                | `code/quant_ml/src/quant_ml/risk/hybrid.py`              | `/api/v1/quant/risk/hybrid`                   | [examples/AI_OPTIMIZATION.md](examples/AI_OPTIMIZATION.md)     | Consistent portfolio weights        |
| **Market Forecasting**     | Validated price forecasts with intervals        | `code/quant_ml/src/quant_ml/forecasting/price.py`        | `/api/v1/optimization/forecast/<ticker>`      | [examples/AI_OPTIMIZATION.md](examples/AI_OPTIMIZATION.md)     | Naive, drift, ETS, optional Prophet |
| **Sentiment Analysis**     | Finance tuned VADER sentiment                   | `code/quant_ml/src/quant_ml/forecasting/sentiment.py`    | `/api/v1/optimization/sentiment`              | [examples/AI_OPTIMIZATION.md](examples/AI_OPTIMIZATION.md)     | Lexicon based                       |
| **Backtesting**            | Rolling VaR backtests with Kupiec test          | `code/quant_ml/src/quant_ml/risk/engine.py`              | `/api/v1/quant/risk/backtest`                 | [examples/AI_OPTIMIZATION.md](examples/AI_OPTIMIZATION.md)     | Every out of sample day             |
| **Risk Decomposition**     | Volatility, VaR and ES contributions            | `code/quant_ml/src/quant_ml/risk/engine.py`              | `/api/v1/quant/risk/decomposition`            | [examples/AI_OPTIMIZATION.md](examples/AI_OPTIMIZATION.md)     | Contributions sum to total risk     |
| **Reports**                | HTML and PDF reports, scheduling, email         | `code/quant_ml/src/quant_ml/reporting/`                  | `/api/v1/quant/reports/risk`                  | [examples/AI_OPTIMIZATION.md](examples/AI_OPTIMIZATION.md)     | Escaped output, SMTP delivery       |
| **Model Training**         | Train the portfolio optimizer                   | `code/quant_ml/src/quant_ml/training/cli.py`             | `./scripts/model_training.sh -m optimization` | [CLI.md](CLI.md)                                               | Chronological hold out              |
| **Model Evaluation**       | Calibration, backtests, forecast skill          | `code/quant_ml/src/quant_ml/training/evaluate.py`        | `./scripts/model_training.sh --evaluate-only` | [CLI.md](CLI.md)                                               | Exit code 1 with `--strict`         |
| **Extreme Value Theory**   | Tail risk modeling                              | `code/quant_ml/src/quant_ml/risk/evt.py`                 | `/api/v1/quant/risk/evt`                      | [examples/ADVANCED_FEATURES.md](examples/ADVANCED_FEATURES.md) | POT and block maxima                |

## Blockchain Features

| Feature                 | Short description           | Module / File                                    | CLI flag / API        | Example (path)                                                 | Notes                        |
| ----------------------- | --------------------------- | ------------------------------------------------ | --------------------- | -------------------------------------------------------------- | ---------------------------- |
| **Portfolio Tracker**   | On-chain portfolio storage  | `code/blockchain/contracts/PortfolioTracker.sol` | Smart contract        | [examples/ADVANCED_FEATURES.md](examples/ADVANCED_FEATURES.md) | Ethereum/Solidity            |
| **Risk Management**     | On-chain risk calculation   | `code/blockchain/contracts/RiskManagement.sol`   | Smart contract        | [examples/ADVANCED_FEATURES.md](examples/ADVANCED_FEATURES.md) | Chainlink oracle integration |
| **Web3 Integration**    | Python blockchain interface | `code/blockchain/web3_integration.py`            | Python lib            | [examples/ADVANCED_FEATURES.md](examples/ADVANCED_FEATURES.md) | web3.py wrapper              |
| **Transaction History** | Immutable audit trail       | `code/blockchain/contracts/PortfolioTracker.sol` | Smart contract events | -                                                              | Event logging                |
| **Contract Deployment** | Deploy to networks          | `code/blockchain/`                               | `npx hardhat deploy`  | [CLI.md](CLI.md)                                               | Localhost, testnet, mainnet  |
| **Contract Testing**    | Smart contract tests        | `code/blockchain/tests/`                         | `npx hardhat test`    | [CLI.md](CLI.md)                                               | Truffle/Hardhat tests        |

## Infrastructure Features

| Feature                    | Short description              | Module / File                                              | CLI flag / API         | Example (path)                     | Notes                |
| -------------------------- | ------------------------------ | ---------------------------------------------------------- | ---------------------- | ---------------------------------- | -------------------- |
| **Docker Support**         | Containerized deployment       | `docker-compose.yml`                                       | `docker-compose up`    | [INSTALLATION.md](INSTALLATION.md) | All services         |
| **Celery Tasks**           | Async task processing          | `code/backend/src/tasks/`                                  | `celery worker`        | [CLI.md](CLI.md)                   | Redis broker         |
| **Health Checks**          | Service status monitoring      | `code/backend/app.py`                                      | `/health`              | [API.md](API.md)                   | DB & cache status    |
| **Performance Monitoring** | Prometheus metrics             | `code/backend/src/utils/performance.py`                    | `/api/v1/monitoring/*` | [API.md](API.md)                   | Admin only           |
| **Error Handling**         | Structured error responses     | `code/backend/src/api/middleware/error_middleware.py`      | All endpoints          | [API.md](API.md)                   | Standard format      |
| **Rate Limiting**          | Request throttling             | `code/backend/src/api/middleware/rate_limit_middleware.py` | All API endpoints      | [API.md](API.md)                   | 60/min default       |
| **Logging**                | Structured logging             | `code/backend/src/core/logging.py`                         | Application-wide       | -                                  | structlog-based      |
| **CORS**                   | Cross-origin support           | `code/backend/app.py`                                      | API-wide               | -                                  | Configurable origins |
| **API Documentation**      | Swagger/OpenAPI                | `code/backend/app.py`                                      | `/apidocs`             | http://localhost:5000/apidocs      | Interactive docs     |
| **CI/CD Pipeline**         | Automated testing & deployment | `.github/workflows/`                                       | GitHub Actions         | -                                  | Test, lint, deploy   |
| **Pre-commit Hooks**       | Code quality gates             | `.pre-commit-config.yaml`                                  | Git hooks              | [CLI.md](CLI.md)                   | Formatting, linting  |

## Testing Features

| Feature               | Short description      | Module / File                     | CLI flag / API                      | Example (path)   | Notes                        |
| --------------------- | ---------------------- | --------------------------------- | ----------------------------------- | ---------------- | ---------------------------- |
| **Unit Tests**        | Component-level tests  | `code/backend/tests/`             | `./scripts/run_tests.sh`            | [CLI.md](CLI.md) | pytest-based                 |
| **Integration Tests** | End-to-end workflows   | `code/backend/tests/integration/` | `./scripts/run_tests.sh`            | [CLI.md](CLI.md) | Multi-component tests        |
| **Frontend Tests**    | React component tests  | `web-frontend/__tests__/`         | `npm test`                          | [CLI.md](CLI.md) | Jest + React Testing Library |
| **Contract Tests**    | Smart contract tests   | `code/blockchain/tests/`          | `npx hardhat test`                  | [CLI.md](CLI.md) | Hardhat framework            |
| **Coverage Reports**  | Test coverage metrics  | `code/backend/tests/`             | `./scripts/run_tests.sh --coverage` | [CLI.md](CLI.md) | 85%+ coverage                |
| **Load Testing**      | Performance benchmarks | `code/backend/tests/integration/` | Python lib                          | -                | Concurrent requests          |

## Development Tools

| Feature            | Short description        | Module / File                  | CLI flag / API | Example (path)   | Notes                    |
| ------------------ | ------------------------ | ------------------------------ | -------------- | ---------------- | ------------------------ |
| **Setup Scripts**  | Environment setup        | `scripts/setup_environment.sh` | Shell script   | [CLI.md](CLI.md) | One-command setup        |
| **Code Quality**   | Linting & formatting     | `scripts/code_quality.sh`      | Shell script   | [CLI.md](CLI.md) | flake8, ESLint, Prettier |
| **Deployment**     | Multi-environment deploy | `scripts/deploy.sh`            | Shell script   | [CLI.md](CLI.md) | dev/staging/prod         |
| **Model Training** | AI model training        | `scripts/model_training.sh`    | Shell script   | [CLI.md](CLI.md) | Custom datasets          |

## See Also

- [API.md](API.md) - Complete API reference
- [USAGE.md](USAGE.md) - Usage examples
- [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture
- [examples/](examples/) - Detailed feature examples
