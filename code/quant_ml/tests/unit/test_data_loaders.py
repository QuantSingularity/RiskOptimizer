import pytest
from quant_ml.data.loaders import (
    available_symbols,
    load_close_prices,
    load_close_series,
    normalize_symbol,
)


class TestDataLoaders:
    def test_available_symbols_lists_bundled_data(self):
        symbols = available_symbols()
        assert "AAPL" in symbols and "BTC_USD" in symbols

    def test_normalize_symbol_maps_separators(self):
        assert normalize_symbol("btc-usd") == "BTC_USD"

    @pytest.mark.parametrize("bad", ["../etc/passwd", "A B", "", "x" * 40, None, 5])
    def test_invalid_symbols_rejected(self, bad):
        with pytest.raises(ValueError):
            normalize_symbol(bad)

    def test_missing_symbol_raises(self):
        with pytest.raises(FileNotFoundError):
            load_close_series("NOPE")

    def test_series_is_sorted_unique_positive(self):
        series = load_close_series("AAPL")
        assert series.index.is_monotonic_increasing
        assert series.index.is_unique
        assert (series > 0).all()

    def test_alias_resolves_usd_suffix(self):
        assert len(load_close_series("BTC")) > 0

    def test_load_prices_requires_two_symbols(self):
        with pytest.raises(ValueError):
            load_close_prices(["AAPL", "AAPL"])

    def test_load_prices_inner_joins(self):
        frame = load_close_prices(["AAPL", "BTC_USD"])
        assert not frame.isna().any().any()
        assert list(frame.columns) == ["AAPL", "BTC_USD"]
