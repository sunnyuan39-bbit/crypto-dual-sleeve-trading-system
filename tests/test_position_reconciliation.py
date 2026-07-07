from decimal import Decimal

from dual_sleeve_trader.core.account import ExchangePositionSnapshot
from dual_sleeve_trader.execution.position_reconciliation import PositionReconciler
from dual_sleeve_trader.execution.safe_mode import SafeModeController
from dual_sleeve_trader.storage.position_store import SQLitePositionStore


class FakePositionExchange:
    def __init__(self, positions: list[ExchangePositionSnapshot]) -> None:
        self.positions = positions

    def fetch_position_snapshots(self, symbol: str | None = None) -> list[ExchangePositionSnapshot]:
        if symbol is None:
            return self.positions
        return [position for position in self.positions if position.symbol == symbol]


def position(symbol: str, amount: str) -> ExchangePositionSnapshot:
    return ExchangePositionSnapshot(symbol=symbol, position_side="BOTH", position_amt=Decimal(amount))


def test_position_reconciliation_consistent(tmp_path) -> None:
    store = SQLitePositionStore(tmp_path / "state.sqlite3")
    store.upsert_position(position("BTCUSDT", "0.5"))
    safe_mode = SafeModeController()

    report = PositionReconciler(
        store,
        FakePositionExchange([position("BTCUSDT", "0.5")]),
        safe_mode,
    ).reconcile_positions()

    assert report.consistent
    assert safe_mode.allows_new_entries


def test_position_reconciliation_missing_on_exchange_enters_safe_mode(tmp_path) -> None:
    store = SQLitePositionStore(tmp_path / "state.sqlite3")
    store.upsert_position(position("BTCUSDT", "0.5"))
    safe_mode = SafeModeController()

    report = PositionReconciler(store, FakePositionExchange([]), safe_mode).reconcile_positions()

    assert not report.consistent
    assert report.missing_on_exchange == (("BTCUSDT", "BOTH"),)
    assert not safe_mode.allows_new_entries


def test_position_reconciliation_unknown_on_local_enters_safe_mode(tmp_path) -> None:
    store = SQLitePositionStore(tmp_path / "state.sqlite3")
    safe_mode = SafeModeController()

    report = PositionReconciler(
        store,
        FakePositionExchange([position("ETHUSDT", "1")]),
        safe_mode,
    ).reconcile_positions()

    assert not report.consistent
    assert report.unknown_on_local == (("ETHUSDT", "BOTH"),)
    assert not safe_mode.allows_new_entries


def test_position_reconciliation_amount_mismatch_enters_safe_mode(tmp_path) -> None:
    store = SQLitePositionStore(tmp_path / "state.sqlite3")
    store.upsert_position(position("SOLUSDT", "10"))
    safe_mode = SafeModeController()

    report = PositionReconciler(
        store,
        FakePositionExchange([position("SOLUSDT", "9")]),
        safe_mode,
    ).reconcile_positions()

    assert not report.consistent
    assert report.amount_mismatches == (("SOLUSDT", "BOTH"),)
    assert not safe_mode.allows_new_entries


def test_position_refresh_writes_exchange_positions(tmp_path) -> None:
    store = SQLitePositionStore(tmp_path / "state.sqlite3")
    safe_mode = SafeModeController()
    reconciler = PositionReconciler(
        store,
        FakePositionExchange([position("BNBUSDT", "2")]),
        safe_mode,
    )

    reconciler.refresh_local_positions_from_exchange()

    loaded = store.get_position("BNBUSDT")
    assert loaded is not None
    assert loaded.position_amt == Decimal("2")
