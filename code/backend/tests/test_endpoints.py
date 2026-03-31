from typing import Any
from unittest.mock import MagicMock, patch

import pandas as pd


def test_index(client: Any) -> Any:
    """Test the index route returns a success message."""
    response = client.get("/")
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data["status"] == "success"
    assert "RiskOptimizer API is running" in json_data["message"]


@patch("app.expected_returns")
@patch("app.risk_models")
@patch("app.EfficientFrontier")
def test_optimize_portfolio_success(
    mock_ef: Any, mock_risk_models: Any, mock_expected_returns: Any, client: Any
) -> Any:
    """Test successful portfolio optimization."""
    mock_mu = pd.Series([0.1, 0.2])
    mock_s = pd.DataFrame([[0.1, 0.05], [0.05, 0.2]])
    mock_expected_returns.mean_historical_return.return_value = mock_mu
    mock_risk_models.sample_cov.return_value = mock_s
    mock_ef_instance = MagicMock()
    mock_ef_instance.max_sharpe.return_value = None
    mock_ef_instance.clean_weights.return_value = {"AssetA": 0.6, "AssetB": 0.4}
    mock_ef_instance.portfolio_performance.return_value = (0.15, 0.18, 0.75)
    mock_ef.return_value = mock_ef_instance
    historical_data = {"AssetA": [100, 101, 102, 103], "AssetB": [50, 51, 50, 52]}
    request_data = {"historical_data": historical_data}
    response = client.post("/api/optimize", json=request_data)
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data["status"] == "success"
    assert "optimized_allocation" in json_data
    assert "performance_metrics" in json_data
    assert json_data["optimized_allocation"] == {"AssetA": 0.6, "AssetB": 0.4}
    assert json_data["performance_metrics"]["expected_return"] == 0.15
    mock_expected_returns.mean_historical_return.assert_called_once()
    mock_risk_models.sample_cov.assert_called_once()
    mock_ef.assert_called_once_with(mock_mu, mock_s)
    mock_ef_instance.max_sharpe.assert_called_once()
    mock_ef_instance.clean_weights.assert_called_once()
    mock_ef_instance.portfolio_performance.assert_called_once()


def test_optimize_portfolio_error(client: Any) -> Any:
    """Test portfolio optimization with invalid data."""
    response = client.post("/api/optimize", json={"invalid_data": []})
    assert response.status_code == 400
    json_data = response.get_json()
    assert json_data["status"] == "error"
    assert "historical_data" in json_data["message"]


@patch("app.w3")
def test_get_portfolio_blockchain_success(mock_w3: Any, client: Any) -> Any:
    """Test fetching portfolio from blockchain successfully."""
    mock_address = "0x1234567890123456789012345678901234567890"
    mock_w3.isAddress.return_value = True
    mock_contract_instance = MagicMock()
    mock_contract_instance.functions.getPortfolio().call.return_value = (
        ["ETH", "BTC"],
        [6000, 4000],
    )
    mock_w3.eth.contract.return_value = mock_contract_instance
    response = client.get(f"/api/portfolio/{mock_address}")
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data["status"] == "success"
    assert json_data["portfolio"]["assets"] == ["ETH", "BTC"]
    assert json_data["portfolio"]["allocations"] == [0.6, 0.4]
    mock_w3.isAddress.assert_called_once_with(mock_address)
    mock_w3.eth.contract.assert_called_once()
    mock_contract_instance.functions.getPortfolio(
        mock_address
    ).call.assert_called_once()


@patch("app.w3")
def test_get_portfolio_blockchain_invalid_address(mock_w3: Any, client: Any) -> Any:
    """Test fetching portfolio from blockchain with invalid address."""
    mock_address = "invalid-address"
    mock_w3.isAddress.return_value = False
    response = client.get(f"/api/portfolio/{mock_address}")
    assert response.status_code == 400
    json_data = response.get_json()
    assert json_data["status"] == "error"
    assert "Invalid Ethereum address" in json_data["message"]
    mock_w3.isAddress.assert_called_once_with(mock_address)


@patch("app.w3")
def test_get_portfolio_blockchain_contract_error(mock_w3: Any, client: Any) -> Any:
    """Test fetching portfolio from blockchain with contract error."""
    mock_address = "0x1234567890123456789012345678901234567890"
    mock_w3.isAddress.return_value = True
    mock_w3.eth.contract.side_effect = Exception("Contract Error")
    response = client.get(f"/api/portfolio/{mock_address}")
    assert response.status_code == 500
    json_data = response.get_json()
    assert json_data["status"] == "error"
    assert "Contract Error" in json_data["message"]


@patch("app.db")
def test_get_portfolio_db_success(mock_db: Any, client: Any) -> Any:
    """Test fetching portfolio from database successfully."""
    mock_address = "0xABCDEF..."
    mock_db.get_portfolio.return_value = [
        {"asset_symbol": "AAPL", "percentage": 0.7},
        {"asset_symbol": "GOOG", "percentage": 0.3},
    ]
    response = client.get(f"/api/portfolio/db/{mock_address}")
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data["status"] == "success"
    assert json_data["portfolio"]["user_address"] == mock_address
    assert json_data["portfolio"]["assets"] == ["AAPL", "GOOG"]
    assert json_data["portfolio"]["allocations"] == [0.7, 0.3]
    mock_db.get_portfolio.assert_called_once_with(mock_address)


@patch("app.db")
def test_get_portfolio_db_not_found(mock_db: Any, client: Any) -> Any:
    """Test fetching non-existent portfolio from database."""
    mock_address = "0xNONEXISTENT..."
    mock_db.get_portfolio.return_value = None
    response = client.get(f"/api/portfolio/db/{mock_address}")
    assert response.status_code == 404
    json_data = response.get_json()
    assert json_data["status"] == "error"
    assert "Portfolio not found" in json_data["message"]
    mock_db.get_portfolio.assert_called_once_with(mock_address)


@patch("app.db")
def test_save_portfolio_success(mock_db: Any, client: Any) -> Any:
    """Test saving portfolio to database successfully."""
    mock_db.save_portfolio.return_value = True
    request_data = {
        "user_address": "0xSAVEME",
        "allocations": {"TSLA": 0.5, "MSFT": 0.5},
    }
    response = client.post("/api/portfolio/save", json=request_data)
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data["status"] == "success"
    assert "Portfolio saved successfully" in json_data["message"]
    mock_db.save_portfolio.assert_called_once_with(
        "0xSAVEME", {"TSLA": 0.5, "MSFT": 0.5}
    )


@patch("app.db")
def test_save_portfolio_db_error(mock_db: Any, client: Any) -> Any:
    """Test saving portfolio to database with a DB error."""
    mock_db.save_portfolio.return_value = False
    request_data = {"user_address": "0xFAILME", "allocations": {"AMZN": 1.0}}
    response = client.post("/api/portfolio/save", json=request_data)
    assert response.status_code == 500
    json_data = response.get_json()
    assert json_data["status"] == "error"
    assert "Failed to save portfolio" in json_data["message"]
    mock_db.save_portfolio.assert_called_once()


def test_save_portfolio_bad_request(client: Any) -> Any:
    """Test saving portfolio with missing data."""
    response = client.post("/api/portfolio/save", json={"user_address": "0xMISSING"})
    assert response.status_code == 400
    json_data = response.get_json()
    assert json_data["status"] == "error"
    assert "allocations are required" in json_data["message"]


@patch("app.RiskMetrics")
def test_calculate_var_success(mock_risk_metrics: Any, client: Any) -> Any:
    """Test successful VaR calculation."""
    mock_risk_metrics.calculate_var.return_value = 0.05
    request_data = {"returns": [0.01, -0.02, 0.03, -0.01, 0.02], "confidence": 0.99}
    response = client.post("/api/risk/var", json=request_data)
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data["status"] == "success"
    assert json_data["value_at_risk"] == 0.05
    mock_risk_metrics.calculate_var.assert_called_once_with(
        request_data["returns"], request_data["confidence"]
    )


def test_calculate_var_bad_request(client: Any) -> Any:
    """Test VaR calculation with missing returns data."""
    response = client.post("/api/risk/var", json={"confidence": 0.95})
    assert response.status_code == 400
    json_data = response.get_json()
    assert json_data["status"] == "error"
    assert "Returns data is required" in json_data["message"]
