from decimal import Decimal

from dual_sleeve_trader.core.enums import OrderAction, OrderSide, OrderStatus, OrderType, SleeveId
from dual_sleeve_trader.core.models import OrderIntent, OrderRecord
from dual_sleeve_trader.exchange.binance_testnet import BinanceUsdmTestnetAdapter
from dual_sleeve_trader.execution.repair import OrderRepairEngine, RepairAction, RepairReason
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


def test_repair_updates_local_from_exchange(tmp_path) -> None:
    store = SQLiteOrderStore(tmp_path / "state.sqlite3")
    local = make_order("B_setup123_EN_20260101000000")
    store.upsert_order(local)

    remote = make_order("B_setup123_EN_20260101000000", OrderStatus.FILLED)
    remote.exchange_order_id = "123"
    remote.filled_quantity = Decimal("1")
    remote.average_fill_price = Decimal("1999")
    exchange = BinanceUsdmTestnetAdapter()
    exchange.submit_order(remote)

    safe_mode = SafeModeController()
    recommendation = OrderRepairEngine(store, exchange, safe_mode).repair_by_client_order_id(
        local.client_order_id
    )

    updated = store.get_order(local.client_order_id)
    assert recommendation.action == RepairAction.UPDATED_LOCAL_FROM_EXCHANGE
    assert updated is not None
    assert updated.status == OrderStatus.FILLED
    assert updated.filled_quantity == Decimal("1")
    assert updated.average_fill_price == Decimal("1999")
    assert safe_mode.allows_new_entries


def test_repair_missing_exchange_order_enters_safe_mode(tmp_path) -> None:
    store = SQLiteOrderStore(tmp_path / "state.sqlite3")
    local = make_order("B_setup123_EN_20260101000000")
    store.upsert_order(local)
    safe_mode = SafeModeController()

    recommendation = OrderRepairEngine(
        store,
        BinanceUsdmTestnetAdapter(),
        safe_mode,
    ).repair_by_client_order_id(local.client_order_id)

    assert recommendation.reason == RepairReason.EXCHANGE_ORDER_MISSING
    assert not safe_mode.allows_new_entries


def test_repair_missing_local_order_enters_safe_mode(tmp_path) -> None:
    store = SQLiteOrderStore(tmp_path / "state.sqlite3")
    safe_mode = SafeModeController()

    recommendation = OrderRepairEngine(
        store,
        BinanceUsdmTestnetAdapter(),
        safe_mode,
    ).repair_by_client_order_id("missing")

    assert recommendation.reason == RepairReason.LOCAL_ORDER_MISSING
    assert not safe_mode.allows_new_entries
