# CLI Reference

Command-line interface tools for RiskOptimizer.

## Table of Contents

- [Overview](#overview)
- [Scripts](#scripts)
- [Commands](#commands)
- [Examples](#examples)

## Overview

RiskOptimizer provides several command-line scripts for development, testing, deployment, and operations.

## Scripts

All scripts are located in the `scripts/` directory.

### Available Scripts

| Command                    | Arguments                                              | Description                             | Example                                        |
| -------------------------- | ------------------------------------------------------ | --------------------------------------- | ---------------------------------------------- |
| `setup_environment.sh`     | None                                                   | Set up development environment          | `./scripts/setup_environment.sh`               |
| `setup_dev_environment.sh` | None                                                   | Set up dev environment with extra tools | `./scripts/setup_dev_environment.sh`           |
| `run_riskoptimizer.sh`     | None                                                   | Start all application services          | `./scripts/run_riskoptimizer.sh`               |
| `run_tests.sh`             | `[-c component] [-p] [-q] [--coverage]`                | Run tests                               | `./scripts/run_tests.sh -c backend --coverage` |
| `code_quality.sh`          | `[-c component] [-f] [-s]`                             | Check/fix code quality                  | `./scripts/code_quality.sh -f`                 |
| `deploy.sh`                | `-e env [-c component] [--skip-tests]`                 | Deploy to environment                   | `./scripts/deploy.sh -e prod`                  |
| `model_training.sh`        | `[-m model] [-s symbols] [-d data-dir] [-r tolerance]` | Train and evaluate quant_ml models      | `./scripts/model_training.sh -m optimization`  |
| `lint-all.sh`              | None                                                   | Lint all code                           | `./scripts/lint-all.sh`                        |

## Commands

### Setup Commands

#### setup_environment.sh

Sets up the complete environment for RiskOptimizer.

```bash
./scripts/setup_environment.sh
```

**What it does:**

- Checks system dependencies (Python, Node.js, Git)
- Creates Python virtual environment
- Installs backend dependencies
- Installs frontend dependencies
- Creates default `.env` configuration
- Optionally initializes database

#### setup_dev_environment.sh

Sets up development environment with additional tools.

```bash
./scripts/setup_dev_environment.sh
```

**Additional features:**

- Installs pre-commit hooks
- Configures linting tools (flake8, pylint, ESLint)
- Installs development dependencies
- Sets up IDE configurations

### Application Commands

#### run_riskoptimizer.sh

Starts all application components.

```bash
./scripts/run_riskoptimizer.sh
```

**Starts:**

- Backend API server (port 5000)
- Frontend web app (port 3000)
- Celery worker (if Redis available)
- Redis server (if needed)

**Environment variables:**

- `API_PORT` - Backend port (default: 5000)
- `FRONTEND_PORT` - Frontend port (default: 3000)

### Testing Commands

#### run_tests.sh

Runs tests across components.

```bash
# Run all tests
./scripts/run_tests.sh

# Run tests for specific component
./scripts/run_tests.sh -c backend
./scripts/run_tests.sh -c frontend
./scripts/run_tests.sh -c blockchain

# Run with coverage report
./scripts/run_tests.sh --coverage

# Run in parallel
./scripts/run_tests.sh -p

# Quick tests only (skip slow tests)
./scripts/run_tests.sh -q

# Combine options
./scripts/run_tests.sh -c backend --coverage -q
```

**Options:**

| Flag              | Description                                        | Example      |
| ----------------- | -------------------------------------------------- | ------------ |
| `-c, --component` | Specify component (backend/frontend/blockchain/ai) | `-c backend` |
| `-p, --parallel`  | Run tests in parallel                              | `-p`         |
| `-q, --quick`     | Run quick tests only                               | `-q`         |
| `--coverage`      | Generate coverage reports                          | `--coverage` |
| `-h, --help`      | Show help message                                  | `-h`         |

**Output:**

- Test results summary
- Coverage reports (if `--coverage` specified)
- Logs in `logs/tests/`

### Code Quality Commands

#### code_quality.sh

Checks and fixes code quality issues.

```bash
# Check all code
./scripts/code_quality.sh

# Check specific component
./scripts/code_quality.sh -c backend
./scripts/code_quality.sh -c frontend

# Auto-fix issues
./scripts/code_quality.sh -f

# Check only staged files (for pre-commit)
./scripts/code_quality.sh -s

# Combine options
./scripts/code_quality.sh -c backend -f
```

**Options:**

| Flag              | Description                   | Example       |
| ----------------- | ----------------------------- | ------------- |
| `-c, --component` | Check specific component      | `-c frontend` |
| `-f, --fix`       | Auto-fix issues when possible | `-f`          |
| `-s, --staged`    | Check only staged files       | `-s`          |

**Tools used:**

- **Python:** flake8, pylint, black, isort
- **JavaScript/TypeScript:** ESLint, Prettier
- **Solidity:** Solhint

#### lint-all.sh

Runs all linters across the project.

```bash
./scripts/lint-all.sh
```

**Checks:**

- Python code style (PEP 8)
- JavaScript/TypeScript style
- Solidity smart contracts
- Configuration files

### Deployment Commands

#### deploy.sh

Deploys application to specified environment.

```bash
# Deploy all to development
./scripts/deploy.sh -e dev

# Deploy all to staging
./scripts/deploy.sh -e staging

# Deploy all to production
./scripts/deploy.sh -e prod

# Deploy specific component
./scripts/deploy.sh -e staging -c backend

# Skip tests before deployment
./scripts/deploy.sh -e prod --skip-tests
```

**Options:**

| Flag                | Description                           | Example        |
| ------------------- | ------------------------------------- | -------------- |
| `-e, --environment` | Target environment (dev/staging/prod) | `-e prod`      |
| `-c, --component`   | Deploy specific component             | `-c backend`   |
| `--skip-tests`      | Skip running tests                    | `--skip-tests` |

**Prerequisites:**

- Proper credentials configured
- Target environment set up
- Docker/Kubernetes configured (for prod)

### Quant Model Commands

#### model_training.sh

Trains the portfolio optimizer and evaluates the quant_ml models. It wraps `python -m quant_ml.training.cli` and `python -m quant_ml.training.evaluate`.

```bash
# Train the optimizer and evaluate everything
./scripts/model_training.sh

# Train on chosen symbols with a given risk tolerance
./scripts/model_training.sh -m optimization -s AAPL MSFT BTC_USD -r 7

# Use your own data (directory of <SYMBOL>_historical.csv files)
./scripts/model_training.sh -d /path/to/data -s AAPL MSFT

# Evaluate only, failing the run if any calibration check fails
./scripts/model_training.sh --evaluate-only --strict

# Save efficient frontier and Monte Carlo plots after training
./scripts/model_training.sh -m optimization --visualize
```

**Options:**

| Flag                   | Description                                          | Example              |
| ---------------------- | ---------------------------------------------------- | -------------------- |
| `-m, --model`          | `all`, `optimization`, `risk` or `forecast`          | `-m optimization`    |
| `-s, --symbols`        | Space separated symbols (default: every dataset)     | `-s AAPL MSFT`       |
| `-d, --data-dir`       | Directory containing `<SYMBOL>_historical.csv` files | `-d ./data`          |
| `-r, --risk-tolerance` | Risk tolerance from 1 to 10 used in training         | `-r 7`               |
| `-o, --model-path`     | Where to save the trained optimizer                  | `-o model.joblib`    |
| `--output-dir`         | Where to write `evaluation.json`                     | `--output-dir ./out` |
| `--evaluate-only`      | Skip training                                        | `--evaluate-only`    |
| `--no-metrics`         | Skip the evaluation step                             | `--no-metrics`       |
| `--strict`             | Exit with an error if any calibration check fails    | `--strict`           |
| `--visualize`          | Save plots after training                            | `--visualize`        |

**Model types:**

- `optimization` - trains and saves the ML portfolio optimizer
- `risk` and `forecast` - fitted on demand per request, so they are evaluated only
- `all` - trains the optimizer, then evaluates everything

**Output:**

- The trained optimizer at `code/quant_ml/artifacts/portfolio_optimizer.joblib` (or `-o`)
- `evaluation.json` with calibration, backtest and forecast results
- The evaluation prints a pass or fail line for each check

## Python CLI (Direct)

### Backend App

Start the Flask application directly:

```bash
cd code/backend
python app.py

# With environment variables
API_PORT=8000 python app.py

# With debug mode
FLASK_DEBUG=1 python app.py
```

### Database Management

```bash
cd code/backend

# Initialize database
python -c "from src.infrastructure.database.session import init_db; init_db()"

# Run migrations (if using Alembic)
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

### Celery Worker

```bash
cd code/backend

# Start Celery worker
celery -A src.tasks.celery_app worker --loglevel=info

# With multiple workers
celery -A src.tasks.celery_app worker --loglevel=info --concurrency=4

# Beat scheduler (for periodic tasks)
celery -A src.tasks.celery_app beat --loglevel=info
```

## Node.js CLI (Frontend)

### Web Frontend

```bash
cd web-frontend

# Development server
npm start

# Production build
npm run build

# Run tests
npm test

# Lint code
npm run lint

# Fix lint issues
npm run lint:fix
```

### Mobile Frontend

```bash
cd mobile-frontend

# Start Expo server
npm start

# Run on Android
npm run android

# Run on iOS
npm run ios

# Build for production
npm run build
```

## Blockchain CLI

### Smart Contracts

```bash
cd code/blockchain

# Compile contracts
npx hardhat compile

# Run tests
npx hardhat test

# Deploy to local network
npx hardhat run scripts/deploy.js --network localhost

# Deploy to testnet (Goerli)
npx hardhat run scripts/deploy.js --network goerli

# Deploy to mainnet
npx hardhat run scripts/deploy.js --network mainnet

# Verify contract
npx hardhat verify --network goerli CONTRACT_ADDRESS
```

## Docker Commands

```bash
# Start all services
docker-compose up -d

# Start specific service
docker-compose up -d backend

# View logs
docker-compose logs -f backend

# Stop all services
docker-compose down

# Rebuild and start
docker-compose up -d --build

# Remove volumes
docker-compose down -v
```

## Examples

### Example 1: Complete Development Setup

```bash
# 1. Clone repository
git clone https://github.com/quantsingularity/RiskOptimizer.git
cd RiskOptimizer

# 2. Run development setup
./scripts/setup_dev_environment.sh

# 3. Start application
./scripts/run_riskoptimizer.sh

# 4. In another terminal, run tests
./scripts/run_tests.sh -c backend --coverage

# 5. Check code quality
./scripts/code_quality.sh
```

### Example 2: Train and Deploy Model

```bash
# 1. Train the optimizer on your symbols
./scripts/model_training.sh -m optimization -s AAPL MSFT GOOGL BTC_USD -r 6

# 2. Check calibration and fail on any problem
./scripts/model_training.sh --evaluate-only --strict

# 3. If satisfied, deploy to staging
./scripts/deploy.sh -e staging -c backend
```

### Example 3: Pre-deployment Checklist

```bash
# 1. Run all tests
./scripts/run_tests.sh --coverage

# 2. Check code quality
./scripts/code_quality.sh

# 3. Run security checks (if available)
# npm audit (for Node.js dependencies)
# safety check (for Python dependencies)

# 4. Build production assets
cd web-frontend && npm run build

# 5. Deploy to production
cd ../..
./scripts/deploy.sh -e prod
```

## Environment Variables

Common environment variables used by CLI tools:

| Variable            | Default                  | Description                    |
| ------------------- | ------------------------ | ------------------------------ |
| `API_PORT`          | 5000                     | Backend API port               |
| `FRONTEND_PORT`     | 3000                     | Frontend port                  |
| `DB_USE_SQLITE`     | true                     | Use SQLite (dev) vs PostgreSQL |
| `REDIS_HOST`        | localhost                | Redis server host              |
| `CELERY_BROKER_URL` | redis://localhost:6379/0 | Celery broker URL              |

## Troubleshooting

### Common Issues

**Issue: Script permission denied**

```bash
chmod +x scripts/*.sh
```

**Issue: Virtual environment not found**

```bash
cd code/backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
```

**Issue: Port already in use**

```bash
# Find and kill process using port
lsof -ti:5000 | xargs kill -9
```

**Issue: Module not found**

```bash
cd code/backend
pip install -e .
```

## Best Practices

1. **Always run from project root** - Scripts expect to be run from repository root
2. **Use virtual environments** - Isolate Python dependencies
3. **Check logs** - Logs are in `logs/` directory
4. **Test before deploy** - Always run tests before production deployment
5. **Use version control** - Commit changes before running major operations

## Next Steps

- Check [USAGE.md](USAGE.md) for API and library usage
- Read [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines
- See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for issue resolution
