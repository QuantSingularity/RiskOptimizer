// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title  PortfolioTracker
/// @notice On-chain portfolio registry with allocation history and access control.
///         Allocations are stored as basis points (1 bp = 0.01 %, total must equal 10 000).
contract PortfolioTracker {
    // ─── Structs ────────────────────────────────────────────────────────────

    struct Portfolio {
        address owner;
        string[] assets;
        uint256[] allocations; // basis points, sum = 10 000
        uint256 updatedAt; // block.timestamp of last update
        uint256 version; // monotonically increasing revision counter
    }

    struct HistoryEntry {
        string[] assets;
        uint256[] allocations;
        uint256 timestamp;
    }

    // ─── State ──────────────────────────────────────────────────────────────

    mapping(address => Portfolio) private _portfolios;
    mapping(address => HistoryEntry[]) private _history;
    mapping(address => bool) private _authorised; // operators that may update on behalf of users

    address public immutable owner;
    uint256 public constant MAX_ASSETS = 50;
    uint256 public constant BASIS_POINTS = 10_000;

    // ─── Events ─────────────────────────────────────────────────────────────

    event PortfolioUpdated(
        address indexed user,
        uint256 version,
        uint256 timestamp
    );
    event AssetRebalanced(
        address indexed user,
        string asset,
        uint256 newAllocationBps
    );
    event OperatorSet(address indexed operator, bool authorised);

    // ─── Errors ─────────────────────────────────────────────────────────────

    error Unauthorised();
    error InputLengthMismatch();
    error TooManyAssets(uint256 provided, uint256 max);
    error AllocationSumMismatch(uint256 provided, uint256 required);
    error EmptyAssetName();

    // ─── Constructor ─────────────────────────────────────────────────────────

    constructor() {
        owner = msg.sender;
    }

    // ─── Modifiers ───────────────────────────────────────────────────────────

    modifier onlyOwner() {
        if (msg.sender != owner) revert Unauthorised();
        _;
    }

    modifier onlyAuthorisedOrSelf(address user) {
        if (msg.sender != user && !_authorised[msg.sender])
            revert Unauthorised();
        _;
    }

    // ─── External functions ──────────────────────────────────────────────────

    /// @notice Update the caller's own portfolio.
    /// @param _assets      Ordered list of asset symbols (max 50).
    /// @param _allocations Corresponding basis-point weights (must sum to 10 000).
    function updatePortfolio(
        string[] calldata _assets,
        uint256[] calldata _allocations
    ) external {
        _updatePortfolio(msg.sender, _assets, _allocations);
    }

    /// @notice Operator-driven portfolio update (requires prior authorisation).
    function updatePortfolioFor(
        address user,
        string[] calldata _assets,
        uint256[] calldata _allocations
    ) external onlyAuthorisedOrSelf(user) {
        _updatePortfolio(user, _assets, _allocations);
    }

    /// @notice Authorise or revoke an operator address (owner only).
    function setOperator(address operator, bool authorised) external onlyOwner {
        _authorised[operator] = authorised;
        emit OperatorSet(operator, authorised);
    }

    /// @notice Return the current portfolio for a user.
    function getPortfolio(
        address user
    )
        external
        view
        returns (
            string[] memory assets,
            uint256[] memory allocations,
            uint256 updatedAt,
            uint256 version
        )
    {
        Portfolio storage p = _portfolios[user];
        return (p.assets, p.allocations, p.updatedAt, p.version);
    }

    /// @notice Return the number of historical revisions for a user.
    function historyLength(address user) external view returns (uint256) {
        return _history[user].length;
    }

    /// @notice Return a specific historical revision.
    function getHistoryEntry(
        address user,
        uint256 index
    )
        external
        view
        returns (
            string[] memory assets,
            uint256[] memory allocations,
            uint256 timestamp
        )
    {
        HistoryEntry storage h = _history[user][index];
        return (h.assets, h.allocations, h.timestamp);
    }

    /// @notice Check whether an address is an authorised operator.
    function isOperator(address operator) external view returns (bool) {
        return _authorised[operator];
    }

    // ─── Internal ────────────────────────────────────────────────────────────

    function _updatePortfolio(
        address user,
        string[] calldata _assets,
        uint256[] calldata _allocations
    ) internal {
        if (_assets.length != _allocations.length) revert InputLengthMismatch();
        if (_assets.length > MAX_ASSETS)
            revert TooManyAssets(_assets.length, MAX_ASSETS);

        uint256 total;
        for (uint256 i; i < _allocations.length; ++i) {
            if (bytes(_assets[i]).length == 0) revert EmptyAssetName();
            total += _allocations[i];
        }
        if (total != BASIS_POINTS)
            revert AllocationSumMismatch(total, BASIS_POINTS);

        Portfolio storage p = _portfolios[user];

        // Archive current state before overwriting
        if (p.version > 0) {
            _history[user].push(
                HistoryEntry({
                    assets: p.assets,
                    allocations: p.allocations,
                    timestamp: p.updatedAt
                })
            );
        }

        // Write new state
        p.owner = user;
        p.assets = _assets;
        p.allocations = _allocations;
        p.updatedAt = block.timestamp;
        p.version += 1;

        emit PortfolioUpdated(user, p.version, block.timestamp);

        for (uint256 i; i < _assets.length; ++i) {
            emit AssetRebalanced(user, _assets[i], _allocations[i]);
        }
    }
}
