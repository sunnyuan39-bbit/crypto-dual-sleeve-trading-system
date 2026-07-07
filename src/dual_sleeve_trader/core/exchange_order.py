from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from dual_sleeve_trader.core.enums import OrderStatus


@dataclass(frozen=True)
class ExchangeOrderSnapshot:
    client_order_id: str
    symbol: str
    status: OrderStatus
    exchange_order_id: str | None = None
    executed_quantity: Decimal = Decimal("0")
    average_price: Decimal | None = None
