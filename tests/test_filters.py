from decimal import Decimal

import pytest

from dual_sleeve_trader.core.enums import OrderAction, OrderSide, OrderType, SleeveId
from dual_sleeve_trader.core.models import OrderIntent, SymbolFilters
from dual_sleeve_trader.exchange.filters import ExchangeFilterError, normalize_order_intent


def test_normalize_order_intent_floors_quantity_and_price() -> None:
    intent = OrderIntent(
        sleeve_id=SleeveId.A,
        symbol="BTCUSDT",
        side=OrderSide.SELL,
        order_type=OrderType.LIMIT,
        action=OrderAction.ENTRY,
        quantity=Decimal("1.23456"),
        price=Decimal("100.129"),
        setup_id="abcdef123456",
    )
    filters = SymbolFilters("BTCUSDT", Decimal("0.01"), Decimal("0.001"), Decimal("5"))

    normalized = normalize_order_intent(intent, filters)

    assert normalized.quantity == Decimal("1.234")
    assert normalized.price == Decimal("100.12")


def test_normalize_rejects_min_notional() -> None:
    intent = OrderIntent(
        sleeve_id=SleeveId.A,
        symbol="ALTUSDT",
        side=OrderSide.SELL,
        order_type=OrderType.LIMIT,
        action=OrderAction.ENTRY,
        quantity=Decimal("0.1"),
        price=Decimal("10"),
        setup_id="abcdef123456",
    )
    filters = SymbolFilters("ALTUSDT", Decimal("0.01"), Decimal("0.001"), Decimal("5"))

    with pytest.raises(ExchangeFilterError):
        normalize_order_intent(intent, filters)
