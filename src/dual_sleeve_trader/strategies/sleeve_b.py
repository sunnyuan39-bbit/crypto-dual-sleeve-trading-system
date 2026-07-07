from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from dual_sleeve_trader.core.enums import PositionSide


@dataclass(frozen=True)
class SleeveBSignal:
    symbol: str
    side: PositionSide | None
    trigger: str | None
    reason: str


def ema(values: list[Decimal], period: int) -> list[Decimal]:
    if period <= 0:
        raise ValueError("period must be positive")
    if not values:
        return []
    alpha = Decimal("2") / Decimal(period + 1)
    result = [values[0]]
    for value in values[1:]:
        result.append(alpha * value + (Decimal("1") - alpha) * result[-1])
    return result


def regime_from_daily_close(closes: list[Decimal]) -> str:
    if len(closes) < 200:
        return "INSUFFICIENT_DATA"
    e50 = ema(closes, 50)[-1]
    e200 = ema(closes, 200)[-1]
    last = closes[-1]
    if last > e50 > e200:
        return "BULL"
    if last < e50 < e200:
        return "BEAR"
    return "CHOP"


def donchian_signal(
    symbol: str,
    regime: str,
    close_4h: list[Decimal],
    high_4h: list[Decimal],
    low_4h: list[Decimal],
    lookback_bars: int = 120,
) -> SleeveBSignal:
    if regime not in {"BULL", "BEAR"}:
        return SleeveBSignal(symbol, None, None, f"REGIME_{regime}_NO_ENTRY")
    if len(close_4h) < lookback_bars + 1:
        return SleeveBSignal(symbol, None, None, "INSUFFICIENT_4H_DATA")

    if regime == "BULL" and close_4h[-1] > max(high_4h[-lookback_bars - 1 : -1]):
        return SleeveBSignal(symbol, PositionSide.LONG, "DONCHIAN", "20D_4H_BREAKOUT_LONG")
    if regime == "BEAR" and close_4h[-1] < min(low_4h[-lookback_bars - 1 : -1]):
        return SleeveBSignal(symbol, PositionSide.SHORT, "DONCHIAN", "20D_4H_BREAKDOWN_SHORT")
    return SleeveBSignal(symbol, None, None, "NO_ENTRY")
