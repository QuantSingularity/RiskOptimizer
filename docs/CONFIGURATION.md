# Configuration Guide

Complete configuration reference for RiskOptimizer.

## Table of Contents

- [Overview](#overview)
- [Environment Variables](#environment-variables)
- [Configuration Files](#configuration-files)
- [Database Configuration](#database-configuration)
- [Security Configuration](#security-configuration)
- [Blockchain Configuration](#blockchain-configuration)
- [Examples](#examples)

## Overview

RiskOptimizer can be configured through environment variables and configuration files. Configuration is managed through the `riskoptimizer.core.config` module.

## Environment Variables

All environment variables can be set in a `.env` file in the project root or as system environment variables.

### Application Configuration

| Option        | Type    | Default     | Description                                              | Where to set (env/file) |
| ------------- | ------- | ----------- | -------------------------------------------------------- | ----------------------- |
| `ENVIRONMENT` | string  | development | Application environment (development/staging/production) | .env                    |
| `SECRET_KEY`  | string  | (required)  | Application secret key for sessions                      | .env                    |
| `DEBUG`       | boolean | false       | Enable debug mode (do not use in production)             | .env                    |

### API Configuration

| Option               | Type    | Default  | Description                            | Where to set (env/file) |
| -------------------- | ------- | -------- | -------------------------------------- | ----------------------- |
| `API_HOST`           | string  | 0.0.0.0  | API server host                        | .env                    |
| `API_PORT`           | integer | 5000     | API server port                        | .env                    |
| `CORS_ORIGINS`       | string  | \*       | Allowed CORS origins (comma-separated) | .env                    |
| `MAX_CONTENT_LENGTH` | integer | 16777216 | Max request size in bytes (16MB)       | .env                    |

### Database Configuration

| Option            | Type    | Default          | Description                         | Where to set (env/file) |
| ----------------- | ------- | ---------------- | ----------------------------------- | ----------------------- |
| `DB_USE_SQLITE`   | boolean | true             | Use SQLite (dev) vs PostgreSQL      | .env                    |
| `SQLITE_DB_PATH`  | string  | riskoptimizer.db | SQLite database path                | .env                    |
| `DB_HOST`         | string  | localhost        | PostgreSQL host                     | .env                    |
| `DB_PORT`         | integer | 5432             | PostgreSQL port                     | .env                    |
| `DB_NAME`         | string  | riskoptimizer    | Database name                       | .env                    |
| `DB_USER`         | string  | postgres         | Database user                       | .env                    |
| `DB_PASSWORD`     | string  | postgres         | Database password                   | .env                    |
| `DB_POOL_SIZE`    | integer | 10               | Connection pool size                | .env                    |
| `DB_MAX_OVERFLOW` | integer | 20               | Max overflow connections            | .env                    |
| `DB_POOL_TIMEOUT` | integer | 30               | Pool timeout (seconds)              | .env                    |
| `DB_POOL_RECYCLE` | integer | 3600             | Recycle connections after (seconds) | .env                    |

### Redis Configuration

| Option                         | Type    | Default   | Description               | Where to set (env/file) |
| ------------------------------ | ------- | --------- | ------------------------- | ----------------------- |
| `REDIS_HOST`                   | string  | localhost | Redis server host         | .env                    |
| `REDIS_PORT`                   | integer | 6379      | Redis server port         | .env                    |
| `REDIS_DB`                     | integer | 0         | Redis database number     | .env                    |
| `REDIS_PASSWORD`               | string  | null      | Redis password (optional) | .env                    |
| `REDIS_SOCKET_TIMEOUT`         | integer | 30        | Socket timeout (seconds)  | .env                    |
| `REDIS_SOCKET_CONNECT_TIMEOUT` | integer | 30        | Connect timeout (seconds) | .env                    |
| `REDIS_RETRY_ON_TIMEOUT`       | boolean | true      | Retry on timeout          | .env                    |

### Security Configuration

| Option                      | Type    | Default    | Description                             | Where to set (env/file) |
| --------------------------- | ------- | ---------- | --------------------------------------- | ----------------------- |
| `JWT_SECRET_KEY`            | string  | (required) | JWT signing secret                      | .env                    |
| `DATA_ENCRYPTION_KEY`       | string  | (required) | Data encryption key                     | .env                    |
| `JWT_ACCESS_TOKEN_EXPIRES`  | integer | 3600       | Access token expiry (seconds)           | .env                    |
| `JWT_REFRESH_TOKEN_EXPIRES` | integer | 2592000    | Refresh token expiry (seconds, 30 days) | .env                    |
| `PASSWORD_HASH_ROUNDS`      | integer | 12         | Bcrypt hash rounds                      | .env                    |
| `RATE_LIMIT_PER_MINUTE`     | integer | 60         | API rate limit per minute               | .env                    |
| `MAX_LOGIN_ATTEMPTS`        | integer | 5          | Max failed login attempts               | .env                    |
| `LOCKOUT_TIME`              | integer | 300        | Account lockout time (seconds)          | .env                    |

### Blockchain Configuration

| Option                      | Type    | Default               | Description                       | Where to set (env/file) |
| --------------------------- | ------- | --------------------- | --------------------------------- | ----------------------- |
| `BLOCKCHAIN_PROVIDER_URL`   | string  | http://localhost:8545 | Ethereum node URL                 | .env                    |
| `PORTFOLIO_TRACKER_ADDRESS` | string  | (empty)               | PortfolioTracker contract address | .env                    |
| `RISK_MANAGEMENT_ADDRESS`   | string  | (empty)               | RiskManagement contract address   | .env                    |
| `GAS_LIMIT`                 | integer | 500000                | Default gas limit                 | .env                    |
| `GAS_PRICE`                 | integer | 20000000000           | Default gas price (wei)           | .env                    |

### Celery Configuration

| Option                     | Type    | Default                  | Description                 | Where to set (env/file) |
| -------------------------- | ------- | ------------------------ | --------------------------- | ----------------------- |
| `CELERY_BROKER_URL`        | string  | redis://localhost:6379/0 | Message broker URL          | .env                    |
| `CELERY_RESULT_BACKEND`    | string  | redis://localhost:6379/0 | Results backend URL         | .env                    |
| `CELERY_TASK_SERIALIZER`   | string  | json                     | Task serialization format   | .env                    |
| `CELERY_ACCEPT_CONTENT`    | string  | json                     | Accepted content types      | .env                    |
| `CELERY_RESULT_SERIALIZER` | string  | json                     | Result serialization format | .env                    |
| `CELERY_TIMEZONE`          | string  | UTC                      | Celery timezone             | .env                    |
| `CELERY_ENABLE_UTC`        | boolean | true                     | Enable UTC timezone         | .env                    |

### Quant and AI Configuration

| Option                       | Type    | Default                                              | Description                                             | Where to set (env/file) |
| ---------------------------- | ------- | ---------------------------------------------------- | ------------------------------------------------------- | ----------------------- |
| `MODEL_PATH`                 | string  | `code/quant_ml/artifacts/portfolio_optimizer.joblib` | Trained portfolio optimizer file                        | .env                    |
| `AI_AUTO_TRAIN`              | boolean | true                                                 | Train the optimizer on first use when no model exists   | .env                    |
| `QUANT_ML_DATA_DIR`          | string  | bundled datasets                                     | Directory of `<SYMBOL>_historical.csv` files            | .env                    |
| `QUANT_ML_ARTIFACT_DIR`      | string  | `code/quant_ml/artifacts`                            | Where models and reports are written (must be writable) | .env                    |
| `QUANT_ML_REPORT_DIR`        | string  | `<artifact dir>/reports`                             | Report output directory                                 | .env                    |
| `QUANT_ML_N_JOBS`            | integer | 1                                                    | Worker processes used by the parallel risk engine       | .env                    |
| `QUANT_ML_SMTP_HOST`         | string  | unset                                                | SMTP host; with the sender it enables report email      | .env                    |
| `QUANT_ML_SMTP_SENDER`       | string  | unset                                                | From address for emailed reports                        | .env                    |
| `QUANT_ML_SMTP_PORT`         | integer | 587 (465 with SSL)                                   | SMTP port                                               | .env                    |
| `QUANT_ML_SMTP_USER`         | string  | unset                                                | SMTP username                                           | .env                    |
| `QUANT_ML_SMTP_PASSWORD`     | string  | unset                                                | SMTP password                                           | .env                    |
| `QUANT_ML_SMTP_TLS`          | boolean | true                                                 | Use STARTTLS                                            | .env                    |
| `QUANT_ML_SMTP_SSL`          | boolean | false                                                | Use an SSL connection instead of STARTTLS               | .env                    |
| `DAILY_REPORTS_EMAIL_OWNERS` | boolean | false                                                | Email each daily report to the portfolio owner          | .env                    |

## Configuration Files

### .env File

Create a `.env` file in the project root:

```bash
# Application
ENVIRONMENT=development
SECRET_KEY=your-secret-key-here-change-in-production
DEBUG=false

# API
API_HOST=0.0.0.0
API_PORT=5000
CORS_ORIGINS=http://localhost:3000

# Database (SQLite for development)
DB_USE_SQLITE=true
SQLITE_DB_PATH=riskoptimizer.db

# Database (PostgreSQL for production)
# DB_USE_SQLITE=false
# DB_HOST=localhost
# DB_PORT=5432
# DB_NAME=riskoptimizer
# DB_USER=postgres
# DB_PASSWORD=your-secure-password

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
# REDIS_PASSWORD=your-redis-password

# Security
JWT_SECRET_KEY=your-jwt-secret-key-change-in-production
DATA_ENCRYPTION_KEY=your-encryption-key-32-bytes
JWT_ACCESS_TOKEN_EXPIRES=3600
JWT_REFRESH_TOKEN_EXPIRES=2592000
PASSWORD_HASH_ROUNDS=12
RATE_LIMIT_PER_MINUTE=60

# Blockchain (optional)
BLOCKCHAIN_PROVIDER_URL=http://localhost:8545
# PORTFOLIO_TRACKER_ADDRESS=0x...
# RISK_MANAGEMENT_ADDRESS=0x...

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Monitoring (optional)
# SENTRY_DSN=https://...@sentry.io/...
# PROMETHEUS_PORT=9090
```

### .env.example

A template `.env.example` file should be provided in the repository with placeholder values.

## Database Configuration

### SQLite (Development)

For local development, SQLite is used by default:

```env
DB_USE_SQLITE=true
SQLITE_DB_PATH=riskoptimizer.db
```

Database file will be created in the project root.

### PostgreSQL (Production)

For production, use PostgreSQL:

```env
DB_USE_SQLITE=false
DB_HOST=your-db-host
DB_PORT=5432
DB_NAME=riskoptimizer
DB_USER=riskoptimizer_user
DB_PASSWORD=secure-password
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=40
```

#### Connection Pool Settings

| Setting           | Development | Production | Description             |
| ----------------- | ----------- | ---------- | ----------------------- |
| `DB_POOL_SIZE`    | 5-10        | 20-50      | Base connections        |
| `DB_MAX_OVERFLOW` | 10-20       | 40-100     | Additional connections  |
| `DB_POOL_TIMEOUT` | 30          | 60         | Wait timeout (seconds)  |
| `DB_POOL_RECYCLE` | 3600        | 1800       | Recycle after (seconds) |

## Security Configuration

### Generating Secrets

Generate secure secrets for production:

```bash
# Generate SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Generate JWT_SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Generate DATA_ENCRYPTION_KEY (must be 32 bytes)
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### JWT Configuration

Configure JWT token expiry times:

```env
# Short-lived access tokens (1 hour)
JWT_ACCESS_TOKEN_EXPIRES=3600

# Long-lived refresh tokens (30 days)
JWT_REFRESH_TOKEN_EXPIRES=2592000
```

### Rate Limiting

Adjust rate limits based on your needs:

```env
# Requests per minute per IP
RATE_LIMIT_PER_MINUTE=60

# Failed login attempts before lockout
MAX_LOGIN_ATTEMPTS=5

# Lockout duration in seconds (5 minutes)
LOCKOUT_TIME=300
```

## Blockchain Configuration

### Local Development (Hardhat/Ganache)

```env
BLOCKCHAIN_PROVIDER_URL=http://localhost:8545
```

### Testnet (Goerli)

```env
BLOCKCHAIN_PROVIDER_URL=https://goerli.infura.io/v3/YOUR_INFURA_KEY
PORTFOLIO_TRACKER_ADDRESS=0xYourDeployedContractAddress
RISK_MANAGEMENT_ADDRESS=0xYourDeployedContractAddress
```

### Mainnet

```env
BLOCKCHAIN_PROVIDER_URL=https://mainnet.infura.io/v3/YOUR_INFURA_KEY
PORTFOLIO_TRACKER_ADDRESS=0xYourDeployedContractAddress
RISK_MANAGEMENT_ADDRESS=0xYourDeployedContractAddress
GAS_LIMIT=500000
GAS_PRICE=20000000000
```

## Examples

### Development Configuration

```env
ENVIRONMENT=development
DEBUG=true
API_HOST=0.0.0.0
API_PORT=5000
DB_USE_SQLITE=true
SQLITE_DB_PATH=dev.db
REDIS_HOST=localhost
SECRET_KEY=dev-secret-key-change-me
JWT_SECRET_KEY=dev-jwt-secret
DATA_ENCRYPTION_KEY=dev-encryption-key-32-bytes-long
```

### Production Configuration

```env
ENVIRONMENT=production
DEBUG=false
API_HOST=0.0.0.0
API_PORT=5000
CORS_ORIGINS=https://yourdomain.com

# PostgreSQL
DB_USE_SQLITE=false
DB_HOST=prod-db.example.com
DB_PORT=5432
DB_NAME=riskoptimizer_prod
DB_USER=riskoptimizer
DB_PASSWORD=${DB_PASSWORD}
DB_POOL_SIZE=30
DB_MAX_OVERFLOW=60

# Redis
REDIS_HOST=prod-redis.example.com
REDIS_PORT=6379
REDIS_PASSWORD=${REDIS_PASSWORD}

# Security
SECRET_KEY=${SECRET_KEY}
JWT_SECRET_KEY=${JWT_SECRET_KEY}
DATA_ENCRYPTION_KEY=${DATA_ENCRYPTION_KEY}
JWT_ACCESS_TOKEN_EXPIRES=1800
PASSWORD_HASH_ROUNDS=14
RATE_LIMIT_PER_MINUTE=100

# Blockchain
BLOCKCHAIN_PROVIDER_URL=https://mainnet.infura.io/v3/${INFURA_KEY}
PORTFOLIO_TRACKER_ADDRESS=${PORTFOLIO_TRACKER_ADDRESS}
RISK_MANAGEMENT_ADDRESS=${RISK_MANAGEMENT_ADDRESS}
```

### Docker Configuration

When using Docker Compose, use service names as hostnames:

```env
DB_HOST=postgres
REDIS_HOST=redis
BLOCKCHAIN_PROVIDER_URL=http://hardhat:8545
```

## Configuration Best Practices

1. **Never commit secrets** - Use `.env` file and add to `.gitignore`
2. **Use environment-specific files** - `.env.development`, `.env.production`
3. **Generate strong secrets** - Use cryptographic random generators
4. **Validate configuration** - Check required variables at startup
5. **Use secret management** - AWS Secrets Manager, HashiCorp Vault for production
6. **Rotate secrets regularly** - Update JWT secrets, encryption keys periodically
7. **Monitor configuration changes** - Log configuration changes in production
8. **Document custom settings** - Add comments for non-obvious settings

## Configuration Loading

Configuration is loaded in the following order (later sources override earlier):

1. Default values in `config.py`
2. Environment variables
3. `.env` file
4. Command-line arguments (if applicable)

## Troubleshooting

### Issue: Configuration not loaded

**Solution:** Ensure `.env` file is in project root and has correct format.

### Issue: Database connection failed

**Solution:** Verify database credentials and that database server is running.

### Issue: Redis connection failed

**Solution:** Check Redis is running and credentials are correct. Redis is optional.

### Issue: JWT errors

**Solution:** Ensure `JWT_SECRET_KEY` is set and consistent across restarts.

## See Also

- [INSTALLATION.md](INSTALLATION.md) - Installation guide
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Troubleshooting guide
- [API.md](API.md) - API documentation
