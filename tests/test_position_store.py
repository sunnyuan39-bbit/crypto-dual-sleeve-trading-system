from decimal import Decimal

from dual_sleeve_trader.core.account import ExchangePositionSnapshot
from dual_sleeve_trader.storage.position_store import SQLitePositionStore


def test_position_store_round_trips_position(tmp_path) -> None:
    store = SQLitePositionStore(tmp_path / "state.sqlite3")
    position = ExchangePositionSnapshot(
        symbol="BTCUSDT",
        position_side="BOTH",
        position_amt=Decimal("0.5"),
        entry_price=Decimal("100000"),
        mark_price=Decimal("101000"),
        unrealized_profit=Decimal("500"),
        notional=Decimal("50500"),
        isolated_margin=Decimal("0"),
        update_time_ms=123,
    )

    store.upsert_position(position)
    loaded = store.get_position("BTCUSDT")

    assert loaded is not None
    assert loaded.symbol == "BTCUSDT"
    assert loaded.position_amt == Decimal("0.5")
    assert loaded.entry_price == Decimal("100000")


def test_position_store_lists_non_flat_only_by_default(tmp_path) -> None:
    store = SQLitePositionStore(tmp_path / "state.sqlite3")
    store.upsert_position(
        ExchangePositionSnapshot("BTCUSDT", "BOTH", Decimal("0.1"))
    )
    store.upsert_position(
        ExchangePositionSnapshot("ETHUSDT", "BOTH", Decimal("0"))
    )

    positions = store.list_positions()

    assert [position.symbol for position in positions] == ["BTCUSDT"]
    assert len(store.list_positions(include_flat=True)) == 2
