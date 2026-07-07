from decimal import Decimal

from dual_sleeve_trader.core.enums import OrderAction, OrderSide, OrderStatus, OrderType, SleeveId
from dual_sleeve_trader.core.models import OrderIntent, OrderRecord
from dual_sleeve_trader.exchange.binance_testnet import BinanceUsdmTestnetAdapter
from dual_sleeve_trader.execution.reconciliation import OrderReconciler
from dual_sleeve_trader.execution.safe_mode import SafeModeController
from dual_sleeve_trader.storage.sqlite_store import SQLiteOrderStore


def make_order(client_order_id: str, status: OrderStatus = OrderStatus.SUBMITTED) -> OrderRecord:
    intent = OrderIntent(
        sleeve_id=SleeveId.B,
        symbol="ETHUSDT",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        action=OrderAction.ENTRY,
        quantity=Decimal("1"),
        price=Decimal("2000"),
        setup_id="setup12345678",
    )
    return OrderRecord(client_order_id=client_order_id, intent=intent, status=status)


def test_reconciliation_consistent_orders(tmp_path) -> None:
    store = SQLiteOrderStore(tmp_path / "state.sqlite3")
    order = make_order("B_setup123_EN_20260101000000")
    store.upsert_order(order)
    exchange = BinanceUsdmTestnetAdapter()
    exchange.submit_order(order)
    safe_mode = SafeModeController()

    report = OrderReconciler(store, exchange, safe_mode).reconcile_open_orders()

    assert report.consistent
    assert safe_mode.allows_new_entries


def test_reconciliation_missing_exchange_order_enters_safe_mode(tmp_path) -> None:
    store = SQLiteOrderStore(tmp_path / "state.sqlite3")
    order = make_order("B_setup123_EN_20260101000000")
    store.upsert_order(order)
    exchange = BinanceUsdmTestnetAdapter()
    safe_mode = SafeModeController()

    report = OrderReconciler(store, exchange, safe_mode).reconcile_open_orders()

    assert not report.consistent
    assert report.missing_on_exchange == (order.client_order_id,)
    assert not safe_mode.allows_new_entries


def test_reconciliation_unknown_exchange_order_enters_safe_mode(tmp_path) -> None:
    store = SQLiteOrderStore(tmp_path / "state.sqlite3")
    exchange_order = make_order("B_unknown_EN_20260101000000")
    exchange = BinanceUsdmTestnetAdapter()
    exchange.submit_order(exchange_order)
    safe_mode = SafeModeController()

    report = OrderReconciler(store, exchange, safe_mode).reconcile_open_orders()

    assert not report.consistent
    assert report.unknown_on_local == (exchange_order.client_order_id,)
    assert not safe_mode.allows_new_entries
