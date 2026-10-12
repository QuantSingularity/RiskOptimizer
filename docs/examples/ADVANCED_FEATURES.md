# Advanced Features Examples

Advanced usage patterns and features.

## Example 1: Portfolio Optimization

Optimize portfolio allocation using Modern Portfolio Theory.

```python
from quant_ml.data import load_close_prices
from quant_ml.optimization import optimize_weights

prices = load_close_prices(["AAPL", "MSFT", "GOOGL", "AMZN"])
returns = prices.pct_change().dropna()

result = optimize_weights(
    returns,
    "mean_variance",
    {"risk_aversion": 3, "min_weight_per_asset": 0.1, "max_weight_per_asset": 0.4},
)

print("Optimal Allocation:")
for asset, weight in result["weights"].items():
    print(f"  {asset}: {weight * 100:.2f}%")

metrics = result["portfolio_metrics"]
print(f"\nExpected Return: {metrics['expected_return']:.4f}")
print(f"Volatility: {metrics['volatility']:.4f}")
print(f"Sharpe Ratio: {metrics['sharpe_ratio']:.4f}")
print(f"Constraints satisfied: {all(result['constraints_satisfied'].values())}")
```

## Example 2: Monte Carlo Simulation

Run Monte Carlo simulations for risk assessment.

```python
import numpy as np
import pandas as pd

from quant_ml.risk.analysis import monte_carlo_var

rng = np.random.default_rng(0)
returns = pd.DataFrame(
    rng.normal(0.0005, 0.012, size=(500, 3)), columns=["AAPL", "MSFT", "GOOGL"]
)

mc_var = monte_carlo_var(
    returns, confidence_level=0.95, horizon=5, n_simulations=10000, seed=42
)

print("Monte Carlo VaR (95%, 5-day), as a loss fraction:")
print(mc_var)
```

## Example 3: GARCH Volatility Forecasting

Forecast volatility using GARCH models.

```python
from quant_ml.risk.analysis import garch_volatility_forecast, load_returns

returns = load_returns(["AAPL", "MSFT"])

vol_forecast = garch_volatility_forecast(returns, horizon=5)

print("GARCH Volatility Forecast (annualized):")
print(vol_forecast)
```

## Example 4: Stress Testing

Simulate extreme market scenarios.

```python
from quant_ml.risk.analysis import load_returns, stress_test
from quant_ml.risk.stress import stress_portfolio

returns = load_returns(["AAPL", "MSFT", "GOOGL"])

print("Loss implied by a 4x standard deviation shock, per asset:")
print(stress_test(returns, scenario_multiplier=4.0))

portfolio = [0.4, 0.3, 0.3]
outcome = stress_portfolio(
    returns,
    portfolio,
    [
        {"type": "market_crash", "shock": -0.3},
        {"type": "volatility_spike", "multiplier": 2.0},
        {"type": "correlation_breakdown", "intensity": 0.8},
    ],
    seed=1,
)
for item in outcome["stress_results"]:
    print(item["scenario"]["type"], round(item["stressed_var_95"], 4))
```

## Example 5: Blockchain Portfolio Tracking

Store and retrieve portfolio from blockchain.

```python
from code.blockchain.web3_integration import Web3Integration

# Initialize Web3 connection
w3 = Web3Integration(
    provider_url="http://localhost:8545",
    contract_address="0xYourContractAddress"
)

# Update portfolio on blockchain
assets = ['AAPL', 'MSFT', 'GOOGL']
allocations = [3500, 3500, 3000]  # Basis points (35%, 35%, 30%)

try:
    tx_hash = w3.update_portfolio(assets, allocations)
    print(f"Transaction hash: {tx_hash}")

    # Wait for confirmation
    receipt = w3.wait_for_transaction(tx_hash)
    print(f"Transaction confirmed in block {receipt['blockNumber']}")

except Exception as e:
    print(f"Error: {e}")

# Retrieve portfolio from blockchain
user_address = "0xYourWalletAddress"
portfolio = w3.get_portfolio(user_address)
print(f"On-chain portfolio: {portfolio}")
```

## Example 6: Efficient Frontier Calculation

Calculate the efficient frontier for portfolio optimization.

```python
import requests

# API call to calculate efficient frontier
response = requests.post(
    "http://localhost:5000/api/v1/risk/efficient-frontier",
    json={
        "returns": {
            "AAPL": [0.01, 0.02, -0.01, 0.015, 0.025],
            "MSFT": [0.015, 0.01, 0.02, -0.005, 0.018],
            "GOOGL": [0.02, -0.01, 0.015, 0.012, -0.008]
        },
        "num_portfolios": 100
    },
    headers={"Authorization": f"Bearer {TOKEN}"}
)

frontier = response.json()['data']

# Plot results (requires matplotlib)
import matplotlib.pyplot as plt

returns = [p['return'] for p in frontier['portfolios']]
risks = [p['risk'] for p in frontier['portfolios']]

plt.figure(figsize=(10, 6))
plt.scatter(risks, returns, c=returns, cmap='viridis')
plt.xlabel('Risk (Volatility)')
plt.ylabel('Expected Return')
plt.title('Efficient Frontier')
plt.colorbar(label='Return')
plt.show()
```

## Example 7: Extreme Value Theory

Model tail risks using Extreme Value Theory.

```python
import numpy as np

from quant_ml.risk.evt import ExtremeValueRisk

rng = np.random.default_rng(1)
returns = rng.standard_t(4, size=5000) * 0.01

model = ExtremeValueRisk(seed=0).fit_pot(returns, threshold_quantile=0.05)
print(f"GPD shape and scale: {model.gpd_params}")
print(f"VaR (99.9%): {model.calculate_var(0.999):.4f}")
print(f"Expected shortfall (99%): {model.calculate_es(0.99):.4f}")

block = ExtremeValueRisk()
block.fit_block_maxima(returns, block_size=20)
print(f"Block maxima VaR (99%): {block.calculate_var(0.99):.4f}")
```

## Example 8: Async Task Execution

Use Celery for long-running calculations.

```python
from src.tasks.maintenance_tasks import calculate_portfolio_metrics

# Submit task to Celery
task = calculate_portfolio_metrics.delay(
    portfolio_id=1,
    metrics=['var', 'cvar', 'sharpe', 'max_drawdown']
)

print(f"Task ID: {task.id}")

# Check task status
status = task.status
print(f"Status: {status}")

# Get result when ready
if task.ready():
    result = task.get()
    print(f"Metrics: {result}")
```

See [AI_OPTIMIZATION.md](AI_OPTIMIZATION.md) for AI/ML examples.
