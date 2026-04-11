"""
Blockchain Integration Service for RiskOptimizer

This service provides integration with blockchain smart contracts for:
1. Portfolio tracking on the blockchain
2. Risk management calculations
3. Transaction handling and verification
4. Multi-chain support for portfolio diversification
"""

import json
import logging
import os
from typing import Any

from dotenv import load_dotenv
from eth_account import Account
from web3 import HTTPProvider, Web3

try:
    from web3.middleware import ExtraDataToPOAMiddleware
except ImportError:
    try:
        from web3.middleware.proof_of_authority import ExtraDataToPOAMiddleware
    except ImportError:
        ExtraDataToPOAMiddleware = None

try:
    from web3.gas_strategies.time_based import medium_gas_price_strategy
except ImportError:
    medium_gas_price_strategy = None

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

load_dotenv()

PORTFOLIO_TRACKER_ABI = json.loads(
    '\n[\n    {\n      "anonymous": false,\n      "inputs": [\n        {\n          "indexed": true,\n          "internalType": "address",\n          "name": "owner",\n          "type": "address"\n        },\n        {\n          "indexed": false,\n          "internalType": "string",\n          "name": "asset",\n          "type": "string"\n        },\n        {\n          "indexed": false,\n          "internalType": "uint256",\n          "name": "newAllocation",\n          "type": "uint256"\n        }\n      ],\n      "name": "AssetRebalanced",\n      "type": "event"\n    },\n    {\n      "anonymous": false,\n      "inputs": [\n        {\n          "indexed": true,\n          "internalType": "address",\n          "name": "owner",\n          "type": "address"\n        }\n      ],\n      "name": "PortfolioUpdated",\n      "type": "event"\n    },\n    {\n      "inputs": [\n        {\n          "internalType": "address",\n          "name": "user",\n          "type": "address"\n        }\n      ],\n      "name": "getPortfolio",\n      "outputs": [\n        {\n          "internalType": "string[]",\n          "name": "",\n          "type": "string[]"\n        },\n        {\n          "internalType": "uint256[]",\n          "name": "",\n          "type": "uint256[]"\n        }\n      ],\n      "stateMutability": "view",\n      "type": "function"\n    },\n    {\n      "inputs": [\n        {\n          "internalType": "address",\n          "name": "",\n          "type": "address"\n        }\n      ],\n      "name": "portfolios",\n      "outputs": [\n        {\n          "internalType": "address",\n          "name": "owner",\n          "type": "address"\n        },\n        {\n          "internalType": "uint256",\n          "name": "timestamp",\n          "type": "uint256"\n        }\n      ],\n      "stateMutability": "view",\n      "type": "function"\n    },\n    {\n      "inputs": [\n        {\n          "internalType": "string[]",\n          "name": "_assets",\n          "type": "string[]"\n        },\n        {\n          "internalType": "uint256[]",\n          "name": "_allocations",\n          "type": "uint256[]"\n        }\n      ],\n      "name": "updatePortfolio",\n      "outputs": [],\n      "stateMutability": "nonpayable",\n      "type": "function"\n    }\n]\n'
)

RISK_MANAGEMENT_ABI = json.loads(
    '\n[\n    {\n      "inputs": [\n        {\n          "internalType": "address",\n          "name": "_priceFeed",\n          "type": "address"\n        }\n      ],\n      "stateMutability": "nonpayable",\n      "type": "constructor"\n    },\n    {\n      "inputs": [\n        {\n          "internalType": "uint256",\n          "name": "lookbackDays",\n          "type": "uint256"\n        }\n      ],\n      "name": "calculateVolatility",\n      "outputs": [\n        {\n          "internalType": "uint256",\n          "name": "",\n          "type": "uint256"\n        }\n      ],\n      "stateMutability": "view",\n      "type": "function"\n    }\n]\n'
)

DEFAULT_PORTFOLIO_TRACKER_ADDRESS = os.getenv(
    "PORTFOLIO_TRACKER_ADDRESS", "0x1234567890123456789012345678901234567890"
)
DEFAULT_RISK_MANAGEMENT_ADDRESS = os.getenv(
    "RISK_MANAGEMENT_ADDRESS", "0x0987654321098765432109876543210987654321"
)

NETWORKS = {
    "ethereum": {
        "name": "Ethereum Mainnet",
        "rpc_url": os.getenv(
            "ETH_RPC_URL", "https://mainnet.infura.io/v3/your-infura-key"
        ),
        "chain_id": 1,
        "explorer": "https://etherscan.io",
    },
    "polygon": {
        "name": "Polygon Mainnet",
        "rpc_url": os.getenv("POLYGON_RPC_URL", "https://polygon-rpc.com"),
        "chain_id": 137,
        "explorer": "https://polygonscan.com",
    },
    "arbitrum": {
        "name": "Arbitrum One",
        "rpc_url": os.getenv("ARBITRUM_RPC_URL", "https://arb1.arbitrum.io/rpc"),
        "chain_id": 42161,
        "explorer": "https://arbiscan.io",
    },
    "optimism": {
        "name": "Optimism",
        "rpc_url": os.getenv("OPTIMISM_RPC_URL", "https://mainnet.optimism.io"),
        "chain_id": 10,
        "explorer": "https://optimistic.etherscan.io",
    },
    "goerli": {
        "name": "Goerli Testnet",
        "rpc_url": os.getenv(
            "GOERLI_RPC_URL", "https://goerli.infura.io/v3/your-infura-key"
        ),
        "chain_id": 5,
        "explorer": "https://goerli.etherscan.io",
    },
}


def _get_raw_transaction(signed_tx: Any) -> bytes:
    """
    Extract raw transaction bytes from a signed transaction.
    Handles web3.py v5 (.rawTransaction) and v6+ (.raw_transaction).
    """
    if hasattr(signed_tx, "raw_transaction"):
        return signed_tx.raw_transaction
    if hasattr(signed_tx, "rawTransaction"):
        return signed_tx.rawTransaction
    raise AttributeError(
        "Signed transaction object has neither 'raw_transaction' nor 'rawTransaction'."
    )


class BlockchainService:
    """Service for blockchain integration and smart contract interaction."""

    def __init__(self, network: Any = "ethereum") -> None:
        """
        Initialize the blockchain service.

        Args:
            network: Network to connect to (default: ethereum)
        """
        self.network = network
        self.network_config = NETWORKS.get(network, NETWORKS["ethereum"])
        self.w3 = Web3(HTTPProvider(self.network_config["rpc_url"]))

        if ExtraDataToPOAMiddleware is not None:
            try:
                self.w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
            except Exception:
                self.w3.middleware_onion.add(ExtraDataToPOAMiddleware)

        # FIX: guard against None before calling set_gas_price_strategy
        if medium_gas_price_strategy is not None:
            self.w3.eth.set_gas_price_strategy(medium_gas_price_strategy)

        self.portfolio_tracker = self.w3.eth.contract(
            address=Web3.to_checksum_address(DEFAULT_PORTFOLIO_TRACKER_ADDRESS),
            abi=PORTFOLIO_TRACKER_ABI,
        )
        self.risk_management = self.w3.eth.contract(
            address=Web3.to_checksum_address(DEFAULT_RISK_MANAGEMENT_ADDRESS),
            abi=RISK_MANAGEMENT_ABI,
        )

        self.account = None
        private_key = os.getenv("BLOCKCHAIN_PRIVATE_KEY")
        if private_key:
            self.account = Account.from_key(private_key)

    def is_connected(self) -> bool:
        """Check if connected to blockchain network."""
        return self.w3.is_connected()

    def get_network_info(self) -> Any:
        """Get information about the connected network."""
        return {
            "name": self.network_config["name"],
            "chain_id": self.network_config["chain_id"],
            "connected": self.is_connected(),
            "latest_block": self.w3.eth.block_number if self.is_connected() else None,
            "gas_price": self.w3.eth.gas_price if self.is_connected() else None,
        }

    def validate_address(self, address: Any) -> bool:
        """Validate Ethereum address format."""
        return self.w3.is_address(address)

    def get_portfolio(self, address: Any) -> Any:
        """
        Get portfolio from blockchain.

        Args:
            address: User's Ethereum address

        Returns:
            Dictionary with portfolio data
        """
        if not self.validate_address(address):
            raise ValueError("Invalid Ethereum address")
        try:
            assets, allocations = self.portfolio_tracker.functions.getPortfolio(
                Web3.to_checksum_address(address)
            ).call()
            allocations_pct = [allocation / 10000 for allocation in allocations]
            return {
                "user_address": address,
                "assets": assets,
                "allocations": allocations_pct,
                "source": "blockchain",
                "network": self.network_config["name"],
            }
        except Exception as e:
            logger.error(f"Error getting portfolio from blockchain: {e}")
            return None

    def update_portfolio(self, address: Any, assets: Any, allocations_pct: Any) -> Any:
        """
        Update portfolio on blockchain.

        Args:
            address: User's Ethereum address
            assets: List of asset symbols
            allocations_pct: List of allocation percentages (0-100)

        Returns:
            Transaction hash if successful, None otherwise
        """
        if not self.account:
            raise ValueError("Private key not configured for transaction signing")
        if not self.validate_address(address):
            raise ValueError("Invalid Ethereum address")
        if len(assets) != len(allocations_pct):
            raise ValueError("Assets and allocations must have the same length")

        allocations_bp = [int(round(pct * 10000)) for pct in allocations_pct]
        if abs(sum(allocations_bp) - 10000) > 10:
            raise ValueError("Allocations must sum to 100%")

        try:
            tx = self.portfolio_tracker.functions.updatePortfolio(
                assets, allocations_bp
            ).build_transaction(
                {
                    "from": self.account.address,
                    "nonce": self.w3.eth.get_transaction_count(self.account.address),
                    "gas": 2000000,
                    "gasPrice": self.w3.eth.gas_price,
                }
            )
            signed_tx = self.account.sign_transaction(tx)
            # FIX: use helper that handles both web3.py v5 and v6+ attribute names
            raw_tx = _get_raw_transaction(signed_tx)
            tx_hash = self.w3.eth.send_raw_transaction(raw_tx)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            return {
                "tx_hash": tx_hash.hex(),
                "status": "success" if receipt.status == 1 else "failed",
                "block_number": receipt.blockNumber,
                "gas_used": receipt.gasUsed,
                "explorer_url": f"{self.network_config['explorer']}/tx/{tx_hash.hex()}",
            }
        except Exception as e:
            logger.error(f"Error updating portfolio on blockchain: {e}")
            return None

    def calculate_volatility(self, lookback_days: Any = 30) -> Any:
        """
        Calculate market volatility using on-chain risk management contract.

        Args:
            lookback_days: Number of days to look back

        Returns:
            Volatility value
        """
        try:
            volatility = self.risk_management.functions.calculateVolatility(
                lookback_days
            ).call()
            return volatility
        except Exception as e:
            logger.error(f"Error calculating volatility on blockchain: {e}")
            return None

    def get_transaction_history(self, address: Any, limit: Any = 10) -> Any:
        """
        Get transaction history for an address.

        Args:
            address: User's Ethereum address
            limit: Maximum number of transactions to return

        Returns:
            List of transactions
        """
        if not self.validate_address(address):
            raise ValueError("Invalid Ethereum address")
        try:
            latest_block = self.w3.eth.block_number
            portfolio_filter = (
                self.portfolio_tracker.events.PortfolioUpdated.create_filter(
                    fromBlock=latest_block - 10000,
                    toBlock="latest",
                    argument_filters={"owner": Web3.to_checksum_address(address)},
                )
            )
            events = portfolio_filter.get_all_entries()
            transactions = []
            for event in events[:limit]:
                block = self.w3.eth.get_block(event["blockNumber"])
                tx = self.w3.eth.get_transaction(event["transactionHash"])
                transactions.append(
                    {
                        "tx_hash": event["transactionHash"].hex(),
                        "block_number": event["blockNumber"],
                        "timestamp": block["timestamp"],
                        "event": "PortfolioUpdated",
                        "gas_used": tx["gas"],
                        "explorer_url": f"{self.network_config['explorer']}/tx/{event['transactionHash'].hex()}",
                    }
                )
            return transactions
        except Exception as e:
            logger.error(f"Error getting transaction history: {e}")
            return []

    def get_gas_estimate(self, assets: Any, allocations_pct: Any) -> Any:
        """
        Estimate gas for portfolio update.

        Args:
            assets: List of asset symbols
            allocations_pct: List of allocation percentages (0-100)

        Returns:
            Estimated gas amount
        """
        if not self.account:
            raise ValueError("Private key not configured for transaction signing")
        allocations_bp = [int(pct * 100) for pct in allocations_pct]
        try:
            gas_estimate = self.portfolio_tracker.functions.updatePortfolio(
                assets, allocations_bp
            ).estimate_gas({"from": self.account.address})
            return gas_estimate
        except Exception as e:
            logger.error(f"Error estimating gas: {e}")
            return None

    def switch_network(self, network: Any) -> bool:
        """
        Switch to a different blockchain network.

        Args:
            network: Network name

        Returns:
            True if successful, False otherwise
        """
        if network not in NETWORKS:
            raise ValueError(f"Unsupported network: {network}")
        try:
            self.network = network
            self.network_config = NETWORKS[network]
            self.w3 = Web3(HTTPProvider(self.network_config["rpc_url"]))

            if ExtraDataToPOAMiddleware is not None:
                try:
                    self.w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
                except Exception:
                    self.w3.middleware_onion.add(ExtraDataToPOAMiddleware)

            # FIX: guard against None
            if medium_gas_price_strategy is not None:
                self.w3.eth.set_gas_price_strategy(medium_gas_price_strategy)

            self.portfolio_tracker = self.w3.eth.contract(
                address=Web3.to_checksum_address(DEFAULT_PORTFOLIO_TRACKER_ADDRESS),
                abi=PORTFOLIO_TRACKER_ABI,
            )
            self.risk_management = self.w3.eth.contract(
                address=Web3.to_checksum_address(DEFAULT_RISK_MANAGEMENT_ADDRESS),
                abi=RISK_MANAGEMENT_ABI,
            )
            return self.is_connected()
        except Exception as e:
            logger.error(f"Error switching network: {e}")
            return False

    def get_supported_networks(self) -> Any:
        """Get list of supported blockchain networks."""
        return {
            network: {
                "name": config["name"],
                "chain_id": config["chain_id"],
                "explorer": config["explorer"],
            }
            for network, config in NETWORKS.items()
        }


# FIX: lazy-initialize to avoid module-level crash when network is unreachable
def get_blockchain_service(network: str = None) -> BlockchainService:
    """Create a BlockchainService instance, defaulting to the configured network."""
    _network = network or os.getenv("DEFAULT_BLOCKCHAIN_NETWORK", "ethereum")
    return BlockchainService(network=_network)
