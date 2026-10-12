import os
import sys

QUANT_ML_SRC = os.path.join(
    os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    ),
    "quant_ml",
    "src",
)


def ensure_quant_ml() -> None:
    if os.path.isdir(QUANT_ML_SRC) and QUANT_ML_SRC not in sys.path:
        sys.path.insert(0, QUANT_ML_SRC)
