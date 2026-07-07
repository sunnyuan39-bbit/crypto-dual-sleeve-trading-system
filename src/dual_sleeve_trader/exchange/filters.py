from __future__ import annotations

from decimal import Decimal, ROUND_DOWN

from dual_sleeve_trader.core.models import OrderIntent, SymbolFilters


class ExchangeFilterError(ValueError):
    """Raised when an order cannot pass exchange symbol filters."""


def floor_to_step(value: Decimal, step: Decimal) -> Decimal:
    if step <= 0:
        raise ExchangeFilterError("step must be positive")
    return (value / step).to_integral_value(rounding=ROUND_DOWN) * step


def round_price_to_tick(price: Decimal, tick_size: Decimal) -> Decimal:
    return floor_to_step(price, tick_size)


def normalize_order_intent(intent: OrderIntent, filters: SymbolFilters) -> OrderIntent:
    quantity = floor_to_step(intent.quantity, filters.step_size)
    price = round_price_to_tick(intent.price, filters.tick_size) if intent.price is not None else None

    validation_price = price if price is not None else intent.price
    if validation_price is not None and quantity * validation_price < filters.min_notional:
        raise ExchangeFilterError(
            f"{intent.symbol} order notional {quantity * validation_price} below minNotional "
            f"{filters.min_notional}"
        )
    if quantity <= 0:
        raise ExchangeFilterError(f"{intent.symbol} quantity floors to zero")

    return OrderIntent(
        sleeve_id=intent.sleeve_id,
        symbol=intent.symbol,
        side=intent.side,
        order_type=intent.order_type,
        action=intent.action,
        quantity=quantity,
        price=price,
        reduce_only=intent.reduce_only,
        setup_id=intent.setup_id,
        metadata=dict(intent.metadata),
    )
