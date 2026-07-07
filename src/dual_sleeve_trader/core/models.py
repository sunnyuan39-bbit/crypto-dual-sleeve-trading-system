from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from dual_sleeve_trader.core.enums import OrderAction, OrderSide, OrderStatus, OrderType, PositionSide, SleeveId


def utc_now() -> datetime:
    return datetime.now(tz=UTC)


@dataclass(frozen=True)
class SymbolFilters:
    symbol: str
    tick_size: Decimal
    step_size: Decimal
    min_notional: Decimal


@dataclass(frozen=True)
class OrderIntent:
    sleeve_id: SleeveId
    symbol: str
    side: OrderSide
    order_type: OrderType
    action: OrderAction
    quantity: Decimal
    price: Decimal | None = None
    reduce_only: bool = False
    setup_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class OrderRecord:
    client_order_id: str
    intent: OrderIntent
    status: OrderStatus = OrderStatus.CREATED
    exchange_order_id: str | None = None
    filled_quantity: Decimal = Decimal("0")
    average_fill_price: Decimal | None = None
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    @property
    def remaining_quantity(self) -> Decimal:
        remaining = self.intent.quantity - self.filled_quantity
        return remaining if remaining > 0 else Decimal("0")


@dataclass(frozen=True)
class Position:
    position_id: str
    sleeve_id: SleeveId
    symbol: str
    side: PositionSide
    quantity: Decimal
    average_entry_price: Decimal
    stop_price: Decimal | None = None
    setup_id: str | None = None
    opened_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True)
class SleeveLedgerSnapshot:
    sleeve_id: SleeveId
    starting_equity: Decimal
    realized_pnl: Decimal = Decimal("0")
    unrealized_pnl: Decimal = Decimal("0")
    fees: Decimal = Decimal("0")
    funding: Decimal = Decimal("0")
    daily_pnl: Decimal = Decimal("0")
    weekly_pnl: Decimal = Decimal("0")
    monthly_pnl: Decimal = Decimal("0")


@dataclass(frozen=True)
class AccountSnapshot:
    starting_equity: Decimal
    daily_pnl: Decimal
    sleeves: dict[SleeveId, SleeveLedgerSnapshot]


@dataclass(frozen=True)
class DataPointFreshness:
    name: str
    updated_at: datetime | None
    max_age_seconds: int

    def is_fresh(self, now: datetime | None = None) -> bool:
        if self.updated_at is None:
            return False
        current = now or utc_now()
        return (current - self.updated_at).total_seconds() <= self.max_age_seconds
