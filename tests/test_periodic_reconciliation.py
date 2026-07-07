from decimal import Decimal

from dual_sleeve_trader.core.enums import OrderAction, OrderSide, OrderStatus, OrderType, SleeveId
from dual_sleeve_trader.core.models import OrderIntent, OrderRecord
from dual_sleeve_trader.exchange.binance_testnet import BinanceUsdmTestnetAdapter
from dual_sleeve_trader.execution.periodic_reconciliation import (
    PeriodicReconciliationConfig,
    PeriodicReconciliationLoop,
)
from dual_sleeve_trader.execution.reconciliation import OrderReconciler
from dual_sleeve_trader.execution.reconciliation_runner import ReconciliationRunner
from dual_sleeve_trader.execution.safe_mode import SafeModeController
from dual_sleeve_trader.storage.sqlite_store import SQLiteOrderStore


class MemoryAlerts:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def send(self, message: str) -> None:
        self.messages.append(message)


def make_order() -> OrderRecord:
    intent = OrderIntent(
        sleeve_id=SleeveId.A,
        symbol="LABUSDT",
        side=OrderSide.SELL,
        order_type=OrderType.LIMIT,
        action=OrderAction.ENTRY,
        quantity=Decimal("100"),
        price=Decimal("1.23"),
        setup_id="setup12345678",
    )
    return OrderRecord("A_setup123_EN_20260101000000", intent, status=OrderStatus.SUBMITTED)


def test_periodic_loop_stops_on_mismatch(tmp_path) -> None:
    store = SQLiteOrderStore(tmp_path / "state.sqlite3")
    store.upsert_order(make_order())
    safe_mode = SafeModeController()
    reconciler = OrderReconciler(store, BinanceUsdmTestnetAdapter(), safe_mode)
    runner = ReconciliationRunner(reconciler, MemoryAlerts())
    loop = PeriodicReconciliationLoop(
        runner,
        PeriodicReconciliationConfig(interval_seconds=0, max_iterations=5, stop_on_mismatch=True),
    )

    results = loop.run()

    assert len(results) == 1
    assert not results[0].report.consistent
    assert not safe_mode.allows_new_entries
