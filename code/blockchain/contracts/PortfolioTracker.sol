// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract PortfolioTracker {
    struct Portfolio {
        address owner;
        string[] assets;
        uint256[] allocations;
        uint256 timestamp;
    }

    mapping(address => Portfolio) public portfolios;

    event PortfolioUpdated(address indexed owner);
    event AssetRebalanced(
        address indexed owner,
        string asset,
        uint256 newAllocation
    );

    function updatePortfolio(
        string[] memory _assets,
        uint256[] memory _allocations
    ) external {
        require(_assets.length == _allocations.length, "Invalid input");
        uint256 total = 0;
        for (uint256 i = 0; i < _allocations.length; i++) {
            total += _allocations[i];
        }
        require(total == 10000, "Allocations must sum to 100%"); // Basis points

        portfolios[msg.sender] = Portfolio({
            owner: msg.sender,
            assets: _assets,
            allocations: _allocations,
            timestamp: block.timestamp
        });

        emit PortfolioUpdated(msg.sender);
    }

    function getPortfolio(
        address user
    ) external view returns (string[] memory, uint256[] memory) {
        return (portfolios[user].assets, portfolios[user].allocations);
    }
}
