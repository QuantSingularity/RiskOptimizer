# Basic Usage Examples

Simple examples to get started with RiskOptimizer.

## Example 1: Calculate Portfolio VaR

Calculate Value at Risk for a portfolio.

```python
from src.domain.services.risk_service import risk_service

# Historical daily returns
returns = [-0.02, 0.01, -0.015, 0.03, -0.01, 0.02, -0.005, 0.025, -0.008, 0.012]

# Calculate VaR at 95% confidence
var_95 = risk_service.calculate_var(returns, confidence=0.95)

print(f"VaR (95%): {var_95:.4f}")
# Output: VaR (95%): -0.0180
```

## Example 2: API Call for Risk Metrics

Use the REST API to calculate risk metrics.

```bash
# Login first
curl -X POST http://localhost:5000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "SecureP@ss123"}'

# Save the access_token from response

# Calculate VaR
curl -X POST http://localhost:5000/api/v1/risk/var \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "returns": [-0.02, 0.01, -0.015, 0.03, -0.01],
    "confidence": 0.95
  }'
```

## Example 3: Create and Manage Portfolio

```python
import requests

BASE_URL = "http://localhost:5000/api/v1"
token = "YOUR_ACCESS_TOKEN"

# Create portfolio
portfolio_data = {
    "name": "Tech Growth Portfolio",
    "description": "High-growth technology stocks",
    "assets": [
        {"symbol": "AAPL", "quantity": 50, "price": 175.00},
        {"symbol": "MSFT", "quantity": 30, "price": 380.00},
        {"symbol": "GOOGL", "quantity": 20, "price": 140.00}
    ]
}

response = requests.post(
    f"{BASE_URL}/portfolio",
    json=portfolio_data,
    headers={"Authorization": f"Bearer {token}"}
)

portfolio = response.json()
print(f"Created portfolio ID: {portfolio['data']['id']}")
```

## Example 4: Calculate Multiple Risk Metrics

```python
from src.domain.services.risk_service import risk_service

returns = [0.02, -0.01, 0.015, -0.03, 0.025, -0.008, 0.012, -0.015, 0.018, -0.005]

# VaR
var = risk_service.calculate_var(returns, confidence=0.95)

# CVaR (Expected Shortfall)
cvar = risk_service.calculate_cvar(returns, confidence=0.95)

# Sharpe Ratio (assuming 2% risk-free rate)
sharpe = risk_service.calculate_sharpe_ratio(returns, risk_free_rate=0.02)

# Maximum Drawdown
max_dd = risk_service.calculate_max_drawdown(returns)

print(f"VaR (95%): {var:.4f}")
print(f"CVaR (95%): {cvar:.4f}")
print(f"Sharpe Ratio: {sharpe:.4f}")
print(f"Max Drawdown: {max_dd:.4f}")
```

## Example 5: Using Historical Data

```python
from quant_ml.risk.analysis import historical_var, load_returns

returns = load_returns(["AAPL", "MSFT", "GOOGL"])

var_results = historical_var(returns, confidence_level=0.99, horizon=1)

print("Historical VaR (99%, 1-day), as a loss fraction:")
print(var_results)
```

See [ADVANCED_FEATURES.md](ADVANCED_FEATURES.md) for more complex examples.
