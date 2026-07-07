from __future__ import annotations

from decimal import Decimal


def calc_notional(entry_price: Decimal, stop_price: Decimal, risk_usdt: Decimal) -> Decimal:
    if entry_price <= 0:
        raise ValueError("entry_price must be positive")
    distance = abs(stop_price - entry_price) / entry_price
    if distance <= 0:
        raise ValueError("stop distance must be positive")
    return risk_usdt / distance


def stop_distance_ok(
    entry_price: Decimal,
    stop_price: Decimal,
    min_distance: Decimal = Decimal("0.04"),
    max_distance: Decimal = Decimal("0.18"),
) -> bool:
    distance = abs(stop_price - entry_price) / entry_price
    return min_distance <= distance <= max_distance
