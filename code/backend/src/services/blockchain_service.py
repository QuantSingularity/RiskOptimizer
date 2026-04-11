"""
Blockchain Service proxy for the backend.

The canonical implementation lives in blockchain/services/blockchain_service.py.
This module re-exports it so existing backend imports keep working without change.
"""

import os
import sys

# Ensure the project root (one level above backend/) is on sys.path
_project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from blockchain.services.blockchain_service import (
    NETWORKS,  # noqa: F401
    BlockchainService,
    get_blockchain_service,
)

__all__ = ["BlockchainService", "get_blockchain_service", "NETWORKS"]
