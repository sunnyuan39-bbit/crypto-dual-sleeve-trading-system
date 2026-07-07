from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from dual_sleeve_trader.risk.capacity import CapacitySnapshot, capacity_check


@dataclass(frozen=True)
class SleeveAScanResult:
    symbol: str
    passed: bool
    reason: str


def oi_from_peak_usd(oi_usd_4h: list[Decimal], lookback_bars: int = 180) -> Decimal | None:
    if len(oi_usd_4h) < min(72, lookback_bars):
        return None
    window = oi_usd_4h[-lookback_bars:]
    peak = max(window)
    if peak <= 0:
        return None
    return oi_usd_4h[-1] / peak - Decimal("1")


def price_falling(close_4h: list[Decimal], low_4h: list[Decimal]) -> bool:
    if len(close_4h) < 7 or len(low_4h) < 3:
        return False
    ret_4h = close_4h[-1] / close_4h[-2] - Decimal("1")
    ret_24h = close_4h[-1] / close_4h[-7] - Decimal("1")
    lower_lows = low_4h[-1] < low_4h[-2] < low_4h[-3]
    lower_closes = close_4h[-1] < close_4h[-2] < close_4h[-3]
    return ret_24h <= Decimal("-0.08") or (
        ret_4h <= Decimal("-0.03") and lower_lows and lower_closes
    )


def apply_listing_age_gate(
    listing_age_days: int,
    has_minimum_4h_bars: bool,
    borrow_confidence_low: bool,
) -> SleeveAScanResult | None:
    if listing_age_days < 7:
        return SleeveAScanResult("", False, "NEW_LISTING_LT_7D_NO_TRADE")
    if 7 <= listing_age_days < 30:
        if not has_minimum_4h_bars:
            return SleeveAScanResult("", False, "NEW_LISTING_INSUFFICIENT_4H_BARS")
        if borrow_confidence_low:
            return SleeveAScanResult("", False, "NEW_LISTING_LOW_BORROW_CONFIDENCE")
    return None


def scan_capacity(symbol: str, notional: Decimal, snapshot: CapacitySnapshot) -> SleeveAScanResult:
    if not capacity_check(notional, snapshot):
        return SleeveAScanResult(symbol, False, "CAPACITY_CHECK_FAILED")
    return SleeveAScanResult(symbol, True, "CAPACITY_OK")
