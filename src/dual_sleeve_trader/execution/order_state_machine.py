from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from dual_sleeve_trader.core.enums import OrderStatus
from dual_sleeve_trader.core.models import OrderRecord


class InvalidOrderTransition(RuntimeError):
    pass


_ALLOWED_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.CREATED: {OrderStatus.SUBMITTED, OrderStatus.REJECTED, OrderStatus.UNKNOWN},
    OrderStatus.SUBMITTED: {
        OrderStatus.PARTIALLY_FILLED,
        OrderStatus.FILLED,
        OrderStatus.CANCELED,
        OrderStatus.REJECTED,
        OrderStatus.EXPIRED,
        OrderStatus.UNKNOWN,
    },
    OrderStatus.PARTIALLY_FILLED: {
        OrderStatus.PARTIALLY_FILLED,
        OrderStatus.FILLED,
        OrderStatus.CANCELED,
        OrderStatus.UNKNOWN,
    },
    OrderStatus.FILLED: set(),
    OrderStatus.CANCELED: set(),
    OrderStatus.REJECTED: set(),
    OrderStatus.EXPIRED: set(),
    OrderStatus.UNKNOWN: {OrderStatus.SUBMITTED, OrderStatus.CANCELED, OrderStatus.FILLED},
}


class OrderStateMachine:
    def transition(self, order: OrderRecord, new_status: OrderStatus) -> OrderRecord:
        allowed = _ALLOWED_TRANSITIONS[order.status]
        if new_status not in allowed:
            raise InvalidOrderTransition(f"Cannot transition {order.status} -> {new_status}")
        order.status = new_status
        order.updated_at = datetime.now(tz=UTC)
        return order

    def apply_fill(
        self,
        order: OrderRecord,
        filled_quantity: Decimal,
        average_fill_price: Decimal,
    ) -> OrderRecord:
        if filled_quantity < 0:
            raise ValueError("filled_quantity cannot be negative")
        if filled_quantity > order.intent.quantity:
            raise ValueError("filled_quantity cannot exceed order quantity")

        order.filled_quantity = filled_quantity
        order.average_fill_price = average_fill_price
        status = OrderStatus.FILLED if filled_quantity == order.intent.quantity else OrderStatus.PARTIALLY_FILLED

        if status == order.status == OrderStatus.PARTIALLY_FILLED:
            order.updated_at = datetime.now(tz=UTC)
            return order
        return self.transition(order, status)


def should_cancel_entry_remainder(
    order: OrderRecord,
    elapsed_seconds: int,
    min_fill_ratio: Decimal = Decimal("0.5"),
    max_wait_seconds: int = 30,
) -> bool:
    if elapsed_seconds < max_wait_seconds:
        return False
    if order.intent.quantity <= 0:
        return True
    fill_ratio = order.filled_quantity / order.intent.quantity
    return fill_ratio < min_fill_ratio or order.remaining_quantity > 0
