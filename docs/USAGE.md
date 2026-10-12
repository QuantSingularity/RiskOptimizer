# Usage Guide

Learn how to use RiskOptimizer for portfolio risk management and optimization.

## Table of Contents

- [Getting Started](#getting-started)
- [Web Interface Usage](#web-interface-usage)
- [API Usage](#api-usage)
- [Python Library Usage](#python-library-usage)
- [Common Workflows](#common-workflows)
- [Examples](#examples)

## Getting Started

After installation, RiskOptimizer can be used in three ways:

1. **Web Dashboard** - Interactive visual interface
2. **REST API** - Programmatic access via HTTP
3. **Python Library** - Direct Python integration

## Web Interface Usage

### Accessing the Dashboard

1. Start the application:

```bash
./scripts/run_riskoptimizer.sh
```

2. Open your browser to `http://localhost:3000`

3. Login or register a new account

### Dashboard Features

**Portfolio Overview**

- View portfolio composition and allocation
- Real-time performance metrics
- Asset distribution visualization

**Risk Analysis**

- Calculate VaR and CVaR
- View correlation matrices
- Stress testing results
- Volatility forecasts

**Optimization Tool**

- Input portfolio holdings
- Set risk tolerance and constraints
- Generate optimal allocations
- View efficient frontier

**Historical Analysis**

- Performance charts and trends
- Comparative analysis
- Backtesting results

## API Usage

### Authentication

All API endpoints (except `/health`) require JWT authentication.

#### Register a New User

```bash
curl -X POST http://localhost:5000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePass123!",
    "name": "John Doe"
  }'
```

Response:

```json
{
  "status": "success",
  "message": "User registered successfully",
  "data": {
    "user_id": 1,
    "email": "user@example.com"
  }
}
```

#### Login

```bash
curl -X POST http://localhost:5000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePass123!"
  }'
```

Response:

```json
{
  "status": "success",
  "data": {
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "expires_in": 3600
  }
}
```

Save the `access_token` for subsequent requests.

### Risk Calculations

#### Calculate Value at Risk (VaR)

```bash
curl -X POST http://localhost:5000/api/v1/risk/var \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "returns": [-0.02, 0.01, -0.015, 0.03, -0.01, 0.02, -0.005],
    "confidence": 0.95
  }'
```

Response:

```json
{
  "status": "success",
  "data": {
    "var": -0.0234,
    "confidence": 0.95,
    "interpretation": "At 95% confidence, the maximum expected loss is 2.34%"
  }
}
```

#### Calculate Conditional VaR (CVaR)

```bash
curl -X POST http://localhost:5000/api/v1/risk/cvar \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "returns": [-0.02, 0.01, -0.015, 0.03, -0.01, 0.02, -0.005],
    "confidence": 0.95
  }'
```

Response:

```json
{
  "status": "success",
  "data": {
    "cvar": -0.0267,
    "confidence": 0.95,
    "interpretation": "Expected loss given that loss exceeds VaR is 2.67%"
  }
}
```

#### Calculate Sharpe Ratio

```bash
curl -X POST http://localhost:5000/api/v1/risk/sharpe-ratio \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "returns": [0.01, 0.02, -0.01, 0.015, 0.03],
    "risk_free_rate": 0.02
  }'
```

Response:

```json
{
  "status": "success",
  "data": {
    "sharpe_ratio": 1.25,
    "annualized_return": 0.08,
    "annualized_volatility": 0.048
  }
}
```

#### Calculate Maximum Drawdown

```bash
curl -X POST http://localhost:5000/api/v1/risk/max-drawdown \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "returns": [0.02, -0.03, -0.01, 0.04, 0.02, -0.05]
  }'
```

Response:

```json
{
  "status": "success",
  "data": {
    "max_drawdown": -0.089,
    "peak_date": "2024-01-15",
    "trough_date": "2024-02-20",
    "recovery_date": "2024-03-10"
  }
}
```

### Portfolio Operations

#### Create Portfolio

```bash
curl -X POST http://localhost:5000/api/v1/portfolio \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "name": "My Tech Portfolio",
    "assets": [
      {"symbol": "AAPL", "quantity": 10, "price": 175.50},
      {"symbol": "MSFT", "quantity": 15, "price": 380.20},
      {"symbol": "GOOGL", "quantity": 8, "price": 140.30}
    ]
  }'
```

#### Get Portfolio

```bash
curl -X GET http://localhost:5000/api/v1/portfolio/user/1 \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Optimization

#### Optimize Portfolio

```bash
curl -X POST http://localhost:5000/api/v1/monitoring/optimize \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "assets": ["AAPL", "MSFT", "GOOGL", "AMZN"],
    "current_weights": [0.3, 0.3, 0.2, 0.2],
    "objective": "maximize_sharpe",
    "constraints": {
      "max_weight": 0.4,
      "min_weight": 0.1
    }
  }'
```

Response:

```json
{
  "status": "success",
  "data": {
    "optimal_weights": {
      "AAPL": 0.25,
      "MSFT": 0.35,
      "GOOGL": 0.15,
      "AMZN": 0.25
    },
    "expected_return": 0.12,
    "expected_volatility": 0.18,
    "sharpe_ratio": 1.67
  }
}
```

## Python Library Usage

### Direct API Integration

```python
from src.domain.services.risk_service import risk_service
from src.services.quant_analysis import QuantAnalysis

# Calculate VaR
returns = [-0.02, 0.01, -0.015, 0.03, -0.01, 0.02, -0.005]
var = risk_service.calculate_var(returns, confidence=0.95)
print(f"Value at Risk: {var}")

# Calculate CVaR
cvar = risk_service.calculate_cvar(returns, confidence=0.95)
print(f"Conditional VaR: {cvar}")

# Calculate Sharpe Ratio
sharpe = risk_service.calculate_sharpe_ratio(
    returns=returns,
    risk_free_rate=0.02
)
print(f"Sharpe Ratio: {sharpe}")
```

### Portfolio Optimization

```python
from quant_ml.data import load_close_prices
from quant_ml.optimization import optimize_weights

returns = load_close_prices(["AAPL", "MSFT", "GOOGL", "AMZN"]).pct_change().dropna()

result = optimize_weights(
    returns,
    "mean_variance",
    {"target_return": 0.15, "min_weight_per_asset": 0.1, "max_weight_per_asset": 0.4},
)

print("Optimal Allocation:")
for asset, weight in result["weights"].items():
    print(f"  {asset}: {weight * 100:.2f}%")
```

### Risk Analysis

```python
from quant_ml.risk.analysis import (
    calculate_correlation_matrix,
    historical_var,
    load_returns,
    monte_carlo_var,
    stress_test,
)

returns = load_returns(["AAPL", "MSFT", "GOOGL"])

corr_matrix = calculate_correlation_matrix(returns)

hist_var = historical_var(returns, confidence_level=0.99)
mc_var = monte_carlo_var(returns, confidence_level=0.95, n_simulations=10000, seed=1)

stress_results = stress_test(returns, scenario_multiplier=3.0)

print(f"Historical VaR:\n{hist_var}")
print(f"Monte Carlo VaR:\n{mc_var}")
print(f"Stress Test Results:\n{stress_results}")
```

## Common Workflows

### Workflow 1: Daily Risk Assessment

```bash
# Step 1: Calculate current portfolio risk metrics
curl -X POST http://localhost:5000/api/v1/risk/metrics \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer TOKEN" \
  -d '{
    "portfolio_id": 1,
    "metrics": ["var", "cvar", "sharpe_ratio", "max_drawdown"]
  }'

# Step 2: Review results and compare to thresholds
# Step 3: Generate risk report (automated via Celery)
```

### Workflow 2: Portfolio Rebalancing

```bash
# Step 1: Get current portfolio
curl -X GET http://localhost:5000/api/v1/portfolio/user/1 \
  -H "Authorization: Bearer TOKEN"

# Step 2: Run optimization
curl -X POST http://localhost:5000/api/v1/monitoring/optimize \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer TOKEN" \
  -d '{...}'

# Step 3: Review recommendations
# Step 4: Update portfolio
curl -X PUT http://localhost:5000/api/v1/portfolio/1 \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer TOKEN" \
  -d '{...}'
```

### Workflow 3: Scenario Analysis

```python
# Python script for scenario analysis
from src.domain.services.risk_service import risk_service
import numpy as np

# Current portfolio returns
returns = load_portfolio_returns(portfolio_id=1)

# Scenario 1: Market crash (-20%)
crash_returns = returns - 0.20
crash_var = risk_service.calculate_var(crash_returns)

# Scenario 2: Increased volatility (+50%)
volatile_returns = returns + np.random.normal(0, 0.5, len(returns))
volatile_var = risk_service.calculate_var(volatile_returns)

# Scenario 3: Bull market (+15%)
bull_returns = returns + 0.15
bull_var = risk_service.calculate_var(bull_returns)

print(f"Base VaR: {risk_service.calculate_var(returns)}")
print(f"Crash VaR: {crash_var}")
print(f"Volatile VaR: {volatile_var}")
print(f"Bull VaR: {bull_var}")
```

## Examples

### Example 1: Calculate Portfolio Risk

```python
"""Calculate comprehensive risk metrics for a portfolio."""
from src.domain.services.risk_service import risk_service

# Historical returns for your portfolio
returns = [-0.02, 0.01, -0.015, 0.03, -0.01, 0.02, -0.005, 0.025]

# Calculate VaR at 95% confidence
var_95 = risk_service.calculate_var(returns, confidence=0.95)

# Calculate CVaR (expected shortfall)
cvar_95 = risk_service.calculate_cvar(returns, confidence=0.95)

# Calculate Sharpe Ratio (assuming 2% risk-free rate)
sharpe = risk_service.calculate_sharpe_ratio(returns, risk_free_rate=0.02)

# Calculate Maximum Drawdown
max_dd = risk_service.calculate_max_drawdown(returns)

print(f"VaR (95%): {var_95:.4f}")
print(f"CVaR (95%): {cvar_95:.4f}")
print(f"Sharpe Ratio: {sharpe:.4f}")
print(f"Max Drawdown: {max_dd:.4f}")
```

### Example 2: Optimize Asset Allocation

```python
"""Optimize portfolio using Modern Portfolio Theory."""
from quant_ml.data import load_close_prices
from quant_ml.optimization import optimize_weights

tickers = ["AAPL", "MSFT", "GOOGL", "AMZN"]
returns = load_close_prices(tickers).pct_change().dropna()

result = optimize_weights(
    returns,
    "mean_variance",
    {"target_return": 0.15, "min_weight_per_asset": 0.1, "max_weight_per_asset": 0.4},
)

print("Optimal Allocation:")
for asset, weight in result["weights"].items():
    print(f"  {asset}: {weight * 100:.2f}%")
```

### Example 3: Blockchain Portfolio Tracking

```python
"""Interact with blockchain portfolio tracking."""
from code.blockchain.web3_integration import Web3Integration

# Initialize Web3 connection
w3 = Web3Integration(
    provider_url="http://localhost:8545",
    contract_address="0x..."
)

# Update portfolio on blockchain
assets = ['AAPL', 'MSFT', 'GOOGL']
allocations = [3000, 4000, 3000]  # Basis points (30%, 40%, 30%)

tx_hash = w3.update_portfolio(assets, allocations)
print(f"Transaction hash: {tx_hash}")

# Retrieve portfolio from blockchain
portfolio = w3.get_portfolio(user_address)
print(f"Blockchain Portfolio: {portfolio}")
```

## Advanced Usage

### Custom Risk Models

```python
"""Implement custom risk calculation."""
from src.services.quant_analysis import RiskMetrics
import numpy as np

class CustomRiskModel(RiskMetrics):
    @staticmethod
    def calculate_custom_metric(returns, threshold):
        """Custom risk metric implementation."""
        losses = [r for r in returns if r < threshold]
        if not losses:
            return 0.0
        return np.mean(losses)

# Use custom model
custom_model = CustomRiskModel()
custom_risk = custom_model.calculate_custom_metric(returns, threshold=-0.01)
```

### Batch Processing

```python
"""Process multiple portfolios in batch."""
from src.domain.services.risk_service import risk_service
from concurrent.futures import ThreadPoolExecutor

def calculate_portfolio_risk(portfolio_id):
    returns = get_portfolio_returns(portfolio_id)
    return {
        'portfolio_id': portfolio_id,
        'var': risk_service.calculate_var(returns),
        'sharpe': risk_service.calculate_sharpe_ratio(returns)
    }

portfolio_ids = [1, 2, 3, 4, 5]

with ThreadPoolExecutor(max_workers=5) as executor:
    results = list(executor.map(calculate_portfolio_risk, portfolio_ids))

for result in results:
    print(f"Portfolio {result['portfolio_id']}: VaR={result['var']}, Sharpe={result['sharpe']}")
```

## Best Practices

1. **Authentication**: Always store tokens securely and refresh before expiry
2. **Error Handling**: Check response status and handle errors appropriately
3. **Rate Limiting**: Respect API rate limits (60 requests/minute by default)
4. **Data Validation**: Validate input data before sending to API
5. **Caching**: Use caching for frequently accessed data
6. **Monitoring**: Monitor API health and performance metrics

## Next Steps

- Explore [API.md](API.md) for complete API reference
- Check [examples/](examples/) for more detailed examples
- Read [CONFIGURATION.md](CONFIGURATION.md) for advanced configuration
- See [CLI.md](CLI.md) for command-line interface usage
