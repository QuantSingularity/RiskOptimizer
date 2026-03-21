# RiskOptimizer Backend API Documentation

## Overview

The RiskOptimizer backend is a comprehensive financial risk management and portfolio optimization system built with **Flask**, **Celery**, and modern Python technologies. It provides asynchronous task processing for computationally intensive financial calculations, real-time monitoring, and a scalable architecture.

## Table of Contents

- [Architecture](#architecture)
- [Key Features](#key-features)
- [Installation and Setup](#installation-and-setup)
- [API Documentation](#api-documentation)
- [Configuration](#configuration)
- [Task Processing](#task-processing)
- [Testing](#testing)
- [Security](#security)
- [Performance Optimization](#performance-optimization)
- [License](#license)

## Architecture

The backend is built on a robust, microservices-oriented architecture designed for high throughput and reliability in financial computations.

### System Components

The core technologies driving the backend are summarized below:

| Component              | Technology            | Role                                                                  |
| :--------------------- | :-------------------- | :-------------------------------------------------------------------- |
| **API Framework**      | Flask, Flasgger       | Web framework for REST API and automatic documentation (Swagger UI).  |
| **Asynchronous Tasks** | Celery                | Distributed task queue for running long-running risk calculations.    |
| **Database**           | PostgreSQL            | Primary persistent data storage for user, portfolio, and result data. |
| **Cache/Broker**       | Redis                 | Used as a fast cache layer and the message broker for Celery.         |
| **Monitoring**         | Prometheus, Grafana   | Metrics collection, visualization, and alerting.                      |
| **Authentication**     | JWT (JSON Web Tokens) | Stateless, secure authentication and authorization.                   |

### Key Features

The platform offers a comprehensive suite of financial and technical features:

| Feature Category         | Key Capabilities                                                               | Core Modules/Files                                                 |
| :----------------------- | :----------------------------------------------------------------------------- | :----------------------------------------------------------------- |
| **Risk Calculation**     | Monte Carlo simulations, VaR/CVaR, Stress Testing.                             | `services/quant_analysis.py`, `tasks/risk_tasks.py`                |
| **Portfolio Management** | Optimization (Mean-Variance, Risk Parity), Rebalancing, Performance Analysis.  | `domain/services/portfolio_service.py`, `tasks/portfolio_tasks.py` |
| **Data Persistence**     | User, Portfolio, Transaction data storage and retrieval.                       | `infrastructure/database/models.py`, `db/database.py`              |
| **Reporting**            | Automated PDF and Excel report generation.                                     | `tasks/report_tasks.py`                                            |
| **Scalability**          | Kubernetes-ready deployment, horizontal scaling of API and workers.            | `deployment/kubernetes.yaml`, `docker-compose.yml`                 |
| **Security**             | JWT-based authentication, Role-Based Access Control (RBAC), security scanning. | `api/middleware/auth_middleware.py`, `core/config.py`              |

## Installation and Setup

### Prerequisites

- Python 3.11+
- Docker and Docker Compose
- PostgreSQL 15+
- Redis 7+

### Local Development Setup

1. **Clone the repository**

   ```bash
   git clone https://github.com/quantsingularity/RiskOptimizer.git
   cd RiskOptimizer/code/backend
   ```

2. **Create virtual environment**

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   pip install -r tests/requirements-test.txt
   ```

4. **Set up environment variables**

   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Start services with Docker Compose**

   ```bash
   docker-compose up -d postgres redis
   ```

6. **Run database migrations**

   ```bash
   alembic upgrade head
   ```

7. **Start the application**

   ```bash
   # Start API server
   uvicorn app:app --reload --host 0.0.0.0 --port 8000

   # Start Celery worker (in another terminal)
   celery -A tasks.celery_app worker --loglevel=info

   # Start Celery beat scheduler (in another terminal)
   celery -A tasks.celery_app beat --loglevel=info
   ```

### Docker Deployment

1. **Build and start all services**

   ```bash
   docker-compose up --build
   ```

2. **Access the application**
   - API: http://localhost:8000
   - API Documentation: http://localhost:8000/apidocs/
   - Flower (Celery monitoring): http://localhost:5555
   - Grafana: http://localhost:3000

### Kubernetes Deployment

1. **Apply Kubernetes manifests**

   ```bash
   kubectl apply -f deployment/kubernetes.yaml
   ```

2. **Configure ingress and SSL**
   ```bash
   # Update ingress configuration for your domain
   kubectl apply -f deployment/ingress.yaml
   ```

## API Documentation

### Core API Endpoints Summary

The API is versioned under `/api/v1/` and is organized into logical domains for easy access.

| Domain              | Key Endpoints                     | Primary Functionality                                                           | Controller File            |
| :------------------ | :-------------------------------- | :------------------------------------------------------------------------------ | :------------------------- |
| **Authentication**  | `/auth/login`, `/auth/refresh`    | User login and token management.                                                | `auth_controller.py`       |
| **Portfolios**      | `/portfolios`, `/portfolios/{id}` | CRUD operations for managing user portfolios.                                   | `portfolio_controller.py`  |
| **Risk Tasks**      | `/tasks/risk/*`                   | Triggering and managing asynchronous risk calculations (Monte Carlo, VaR/CVaR). | `risk_controller.py`       |
| **Task Management** | `/tasks/{task_id}/*`              | Checking status, retrieving results, and cancelling running tasks.              | `task_controller.py`       |
| **Monitoring**      | `/monitoring/*`                   | Retrieving system health and performance metrics.                               | `monitoring_controller.py` |

### Authentication

All API endpoints require authentication using JWT tokens.

```bash
# Login to get access token
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "user@example.com", "password": "password"}'

# Use token in subsequent requests
curl -H "Authorization: Bearer <token>" \
  "http://localhost:8000/api/v1/portfolios"
```

### Core Endpoints

#### Portfolio Management

- `GET /api/v1/portfolios` - List portfolios
- `POST /api/v1/portfolios` - Create portfolio
- `GET /api/v1/portfolios/{id}` - Get portfolio details
- `PUT /api/v1/portfolios/{id}` - Update portfolio
- `DELETE /api/v1/portfolios/{id}` - Delete portfolio

#### Risk Analysis

- `POST /api/v1/tasks/risk/monte-carlo` - Start Monte Carlo simulation
- `POST /api/v1/tasks/risk/var-cvar` - Calculate VaR/CVaR
- `POST /api/v1/tasks/risk/stress-test` - Run stress tests
- `POST /api/v1/tasks/risk/efficient-frontier` - Calculate efficient frontier

#### Portfolio Optimization

- `POST /api/v1/tasks/portfolio/optimize` - Optimize portfolio allocation
- `POST /api/v1/tasks/portfolio/rebalance` - Calculate rebalancing transactions
- `POST /api/v1/tasks/portfolio/performance-analysis` - Analyze performance

#### Task Management

- `GET /api/v1/tasks/{task_id}/status` - Get task status
- `GET /api/v1/tasks/{task_id}/result` - Get task result
- `DELETE /api/v1/tasks/{task_id}` - Cancel task
- `GET /api/v1/tasks/active` - List active tasks

#### Monitoring

- `GET /api/v1/monitoring/health` - System health check
- `GET /api/v1/monitoring/performance` - Performance metrics
- `GET /api/v1/monitoring/system` - System resource usage

### Example API Usage

#### Monte Carlo Simulation

```python
import requests

# Start Monte Carlo simulation
response = requests.post(
    "http://localhost:8000/api/v1/tasks/risk/monte-carlo",
    headers={"Authorization": "Bearer <token>"},
    json={
        "portfolio_data": {
            "weights": [0.4, 0.3, 0.3],
            "historical_returns": [[0.01, 0.02, -0.01], ...]
        },
        "num_simulations": 10000,
        "time_horizon": 252
    }
)

task_id = response.json()["data"]["task_id"]

# Check task status
status_response = requests.get(
    f"http://localhost:8000/api/v1/tasks/{task_id}/status",
    headers={"Authorization": "Bearer <token>"}
)

# Get results when complete
if status_response.json()["data"]["status"] == "SUCCESS":
    result_response = requests.get(
        f"http://localhost:8000/api/v1/tasks/{task_id}/result",
        headers={"Authorization": "Bearer <token>"}
    )
    results = result_response.json()["data"]["result"]
```

#### Portfolio Optimization

```python
# Optimize portfolio allocation
response = requests.post(
    "http://localhost:8000/api/v1/tasks/portfolio/optimize",
    headers={"Authorization": "Bearer <token>"},
    json={
        "assets_data": {
            "returns": [[0.01, 0.02, 0.015], ...],
            "asset_names": ["Stock_A", "Stock_B", "Bond_A"]
        },
        "optimization_params": {
            "method": "mean_variance",
            "target_return": 0.08,
            "max_weight_per_asset": 0.4
        }
    }
)
```

## Configuration

### Environment Variables

The key environment variables for configuring the backend are listed below. These are typically loaded from a `.env` file.

| Variable              | Purpose                                                           | Example Value                              |
| :-------------------- | :---------------------------------------------------------------- | :----------------------------------------- |
| `DATABASE_URL`        | Connection string for the PostgreSQL database.                    | `postgresql://user:pass@host:port/db_name` |
| `REDIS_URL`           | Connection string for the Redis instance (cache/broker).          | `redis://localhost:6379/0`                 |
| `JWT_SECRET_KEY`      | Secret key used for signing JWT tokens. **MUST be kept secure.**  | `your-secret-key`                          |
| `JWT_ALGORITHM`       | Algorithm used for JWT signing.                                   | `HS256`                                    |
| `ENVIRONMENT`         | Application environment (e.g., development, staging, production). | `development`                              |
| `MARKET_DATA_API_KEY` | API key for fetching external market data.                        | `your-api-key`                             |

### Application Configuration

The application uses a hierarchical configuration system:

1. **Default settings** in `core/config.py`
2. **Environment-specific** settings in `config/{environment}.py` (if applicable)
3. **Environment variables** override file settings

## Task Processing

The backend leverages **Celery** for all long-running, computationally intensive tasks to ensure the main API remains responsive.

### Celery Queues

Tasks are routed to specific queues based on their type to allow for dedicated worker scaling and resource allocation.

| Queue Name               | Primary Task Type                                | Worker Scaling Strategy                           |
| :----------------------- | :----------------------------------------------- | :------------------------------------------------ |
| **default**              | General tasks, quick operations.                 | Low to Medium (e.g., 2-4 workers)                 |
| **risk_calculations**    | Monte Carlo, VaR/CVaR, Efficient Frontier.       | High (e.g., 8+ workers, high-CPU instances)       |
| **portfolio_operations** | Optimization, rebalancing, performance analysis. | Medium to High (e.g., 4-8 workers)                |
| **report_generation**    | PDF/Excel report generation.                     | Medium (e.g., 2-4 workers, high-memory instances) |
| **maintenance**          | System maintenance, cleanup, data updates.       | Low (e.g., 1-2 workers, scheduled execution)      |

### Task Types

| Category                 | Example Tasks                                                                | Description                                            | Core Task File               |
| :----------------------- | :--------------------------------------------------------------------------- | :----------------------------------------------------- | :--------------------------- |
| **Risk Calculation**     | `monte_carlo_simulation`, `calculate_var_cvar`, `stress_test_portfolio`      | Core financial modeling and risk assessment.           | `tasks/risk_tasks.py`        |
| **Portfolio Management** | `optimize_portfolio`, `rebalance_portfolio`, `analyze_portfolio_performance` | Algorithms for financial decision-making.              | `tasks/portfolio_tasks.py`   |
| **Report Generation**    | `generate_portfolio_report`, `export_portfolio_data`                         | Creating user-facing documents and exports.            | `tasks/report_tasks.py`      |
| **Maintenance**          | `cleanup_expired_tasks`, `update_market_data`                                | Background tasks for system health and data freshness. | `tasks/maintenance_tasks.py` |

### Task Monitoring

Monitor task execution using:

1. **Flower**: Web-based Celery monitoring at http://localhost:5555
2. **API endpoints**: Task status and result endpoints
3. **Prometheus metrics**: Task execution metrics
4. **Grafana dashboards**: Visual monitoring dashboards

## Testing

### Test Structure

The test suite is organized to cover different layers of the application:

| Directory/File                  | Test Type        | Coverage Focus                                                                  |
| :------------------------------ | :--------------- | :------------------------------------------------------------------------------ |
| `tests/unit/`                   | Unit             | Individual functions and services (e.g., `test_auth_service.py`).               |
| `tests/integration/`            | Integration      | End-to-end API calls and component interaction (e.g., `test_portfolio_api.py`). |
| `tests/test_risk_tasks.py`      | Unit/Integration | Risk calculation logic and task execution.                                      |
| `tests/test_portfolio_tasks.py` | Unit/Integration | Portfolio management and optimization algorithms.                               |
| `tests/conftest.py`             | Configuration    | Test fixtures, mock objects, and database setup.                                |
| `tests/performance/`            | Performance/Load | Load testing using tools like Locust.                                           |

### Running Tests

```bash
# Run all tests
pytest

# Run specific test categories using markers
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests only
pytest -m "not slow"    # Exclude slow tests

# Run with coverage
pytest --cov=. --cov-report=html
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
