import pytest
from training.trainer import train_and_evaluate, train_and_save


class TestTrainer:
    def test_train_and_evaluate_reports_metrics(self, prices):
        optimizer, report = train_and_evaluate(prices, 5)
        assert optimizer.trained
        assert set(report) >= {
            "prediction_metrics",
            "portfolio_weights",
            "risk_metrics",
        }
        assert (
            optimizer.training_summary["train_rows"]
            > optimizer.training_summary["test_rows"]
        )

    def test_train_and_save_on_bundled_data(self, tmp_path):
        path = tmp_path / "model.joblib"
        optimizer, _, saved = train_and_save(str(path), ["AAPL", "MSFT", "BTC_USD"])
        assert saved == str(path) and path.exists()
        assert optimizer.training_summary["samples"] > 1000

    def test_short_history_rejected(self, prices):
        with pytest.raises(ValueError):
            train_and_evaluate(prices.head(50), 5)
