from decimal import Decimal

import pytest

from dual_sleeve_trader.core.enums import OrderAction, OrderSide, OrderStatus, OrderType, SleeveId
from dual_sleeve_trader.core.models import OrderIntent, OrderRecord
from dual_sleeve_trader.execution.order_state_machine import (
    InvalidOrderTransition,
    OrderStateMachine,
    should_cancel_entry_remainder,
)


def make_order() -> OrderRecord:
    intent = OrderIntent(
        sleeve_id=SleeveId.B,
        symbol="ETHUSDT",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        action=OrderAction.ENTRY,
        quantity=Decimal("10"),
        price=Decimal("2000"),
        setup_id="setup12345678",
    )
    return OrderRecord(client_order_id="B_setup123_EN_20260101000000", intent=intent)


def test_valid_fill_transition() -> None:
    sm = OrderStateMachine()
    order = make_order()
    sm.transition(order, OrderStatus.SUBMITTED)
    sm.apply_fill(order, Decimal("5"), Decimal("2000"))
    assert order.status == OrderStatus.PARTIALLY_FILLED
    assert order.remaining_quantity == Decimal("5")


def test_invalid_transition_after_filled() -> None:
    sm = OrderStateMachine()
    order = make_order()
    sm.transition(order, OrderStatus.SUBMITTED)
    sm.apply_fill(order, Decimal("10"), Decimal("2000"))
    with pytest.raises(InvalidOrderTransition):
        sm.transition(order, OrderStatus.CANCELED)


def test_partial_fill_timeout_cancels_remainder() -> None:
    order = make_order()
    order.filled_quantity = Decimal("4")
    assert should_cancel_entry_remainder(order, elapsed_seconds=31)
