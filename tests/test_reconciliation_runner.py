from decimal import Decimal

from dual_sleeve_trader.core.enums import OrderAction, OrderSide, OrderStatus, OrderType, SleeveId
from dual_sleeve_trader.core.models import OrderIntent, OrderRecord
from dual_sleeve_trader.exchange.binance_testnet import BinanceUsdmTestnetAdapter
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


def test_reconciliation_runner_alerts_on_mismatch(tmp_path) -> None:
    store = SQLiteOrderStore(tmp_path / "state.sqlite3")
    store.upsert_order(make_order())
    safe_mode = SafeModeController()
    reconciler = OrderReconciler(store, BinanceUsdmTestnetAdapter(), safe_mode)
    alerts = MemoryAlerts()

    result = ReconciliationRunner(reconciler, alerts).run_once()

    assert not result.report.consistent
    assert result.alerted
    assert alerts.messages
    assert not safe_mode.allows_new_entries
