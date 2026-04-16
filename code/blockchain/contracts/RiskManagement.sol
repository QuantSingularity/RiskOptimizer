// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@chainlink/contracts/src/v0.8/interfaces/AggregatorV3Interface.sol";

contract RiskManagement {
    AggregatorV3Interface internal priceFeed;

    constructor(address _priceFeed) {
        priceFeed = AggregatorV3Interface(_priceFeed);
    }

    function calculateVolatility(
        uint256 lookbackDays
    ) external view returns (uint256) {
        uint256 roundId = priceFeed.latestRound();
        uint256[] memory prices = new uint256[](lookbackDays);

        for (uint256 i = 0; i < lookbackDays; i++) {
            (, int256 price, , , ) = priceFeed.getRoundData(roundId - i);
            prices[i] = uint256(price);
        }

        uint256 mean = 0;
        for (uint256 i = 0; i < lookbackDays; i++) {
            mean += prices[i];
        }
        mean /= lookbackDays;

        uint256 variance = 0;
        for (uint256 i = 0; i < lookbackDays; i++) {
            variance += (prices[i] - mean) ** 2;
        }
        variance /= lookbackDays;

        return sqrt(variance);
    }

    function sqrt(uint256 x) internal pure returns (uint256) {
        uint256 z = (x + 1) / 2;
        uint256 y = x;
        while (z < y) {
            y = z;
            z = (x / z + z) / 2;
        }
        return y;
    }
}
