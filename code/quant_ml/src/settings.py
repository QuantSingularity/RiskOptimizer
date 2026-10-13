import os
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_ROOT.parent

TRADING_DAYS = 252
RISK_FREE_RATE = 0.02
DEFAULT_CONFIDENCE_LEVELS = (0.95, 0.99)
MODEL_FILE_NAME = "portfolio_optimizer.joblib"


def data_dir() -> Path:
    configured = os.environ.get("QUANT_ML_DATA_DIR")
    if configured:
        return Path(configured)
    return PACKAGE_ROOT / "data" / "datasets"


def artifact_dir() -> Path:
    configured = os.environ.get("QUANT_ML_ARTIFACT_DIR")
    if configured:
        return Path(configured)
    if (PROJECT_ROOT / "pyproject.toml").is_file():
        return PROJECT_ROOT / "artifacts"
    return Path.home() / ".quant_ml" / "artifacts"


def report_dir() -> Path:
    configured = os.environ.get("QUANT_ML_REPORT_DIR")
    if configured:
        return Path(configured)
    return artifact_dir() / "reports"


def default_model_path() -> Path:
    configured = os.environ.get("MODEL_PATH")
    if configured:
        return Path(configured)
    return artifact_dir() / MODEL_FILE_NAME
