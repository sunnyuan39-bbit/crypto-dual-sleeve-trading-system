from decimal import Decimal

from dual_sleeve_trader.core.account import ExchangePositionSnapshot
from dual_sleeve_trader.exchange.binance_testnet import BinanceUsdmTestnetAdapter


def test_inert_testnet_adapter_defaults_to_no_positions() -> None:
    adapter = BinanceUsdmTestnetAdapter()

    assert adapter.fetch_position_snapshots() == []


def test_inert_testnet_adapter_filters_positions_by_symbol() -> None:
    adapter = BinanceUsdmTestnetAdapter(
        positions=[
            ExchangePositionSnapshot("BTCUSDT", "BOTH", Decimal("0.1")),
            ExchangePositionSnapshot("ETHUSDT", "BOTH", Decimal("0.2")),
        ]
    )

    positions = adapter.fetch_position_snapshots("BTCUSDT")

    assert len(positions) == 1
    assert positions[0].symbol == "BTCUSDT"
