from decimal import Decimal

from dual_sleeve_trader.core.enums import OrderAction, OrderSide, OrderStatus, OrderType, SleeveId
from dual_sleeve_trader.core.models import OrderIntent, OrderRecord
from dual_sleeve_trader.storage.sqlite_store import SQLiteOrderStore


def make_order(client_order_id: str = "A_setup123_EN_20260101000000") -> OrderRecord:
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
    return OrderRecord(client_order_id=client_order_id, intent=intent, status=OrderStatus.SUBMITTED)


def test_sqlite_store_round_trips_order(tmp_path) -> None:
    store = SQLiteOrderStore(tmp_path / "state.sqlite3")
    order = make_order()
    order.exchange_order_id = "123"
    order.filled_quantity = Decimal("25")
    order.average_fill_price = Decimal("1.22")

    store.upsert_order(order)
    loaded = store.get_order(order.client_order_id)

    assert loaded is not None
    assert loaded.client_order_id == order.client_order_id
    assert loaded.intent.sleeve_id == SleeveId.A
    assert loaded.filled_quantity == Decimal("25")
    assert loaded.average_fill_price == Decimal("1.22")


def test_sqlite_store_lists_open_orders_only(tmp_path) -> None:
    store = SQLiteOrderStore(tmp_path / "state.sqlite3")
    open_order = make_order("A_open_EN_20260101000000")
    closed_order = make_order("A_closed_EN_20260101000000")
    closed_order.status = OrderStatus.FILLED

    store.upsert_order(open_order)
    store.upsert_order(closed_order)

    open_ids = {order.client_order_id for order in store.list_open_orders()}
    assert open_ids == {open_order.client_order_id}
