from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from dual_sleeve_trader.core.enums import PositionSide
from dual_sleeve_trader.execution.sleeve_b_allocator import SleeveBSignalCandidate
from dual_sleeve_trader.strategies.sleeve_b import donchian_signal, ema, regime_from_daily_close
from dual_sleeve_trader.strategies.sleeve_b_replay import OhlcBar


@dataclass(frozen=True)
class SleeveBCandidateBuilderConfig:
    donchian_lookback_bars: int = 120
    atr_period: int = 14
    stop_atr_multiple: Decimal = Decimal("2.5")
    require_1h_timing: bool = True
    one_hour_ema_period: int = 20
    max_1h_extension_atr: Decimal = Decimal("1.5")
    entry_offset_bps: Decimal = Decimal("5")


@dataclass(frozen=True)
class SleeveBMarketData:
    symbol: str
    daily_bars: tuple[OhlcBar, ...]
    four_hour_bars: tuple[OhlcBar, ...]
    one_hour_bars: tuple[OhlcBar, ...] = ()


@dataclass(frozen=True)
class SleeveBCandidateBuildResult:
    symbol: str
    candidate: SleeveBSignalCandidate | None
    reason: str


def build_sleeve_b_candidate(
    market_data: SleeveBMarketData,
    config: SleeveBCandidateBuilderConfig | None = None,
) -> SleeveBCandidateBuildResult:
    cfg = config or SleeveBCandidateBuilderConfig()
    if len(market_data.daily_bars) < 200:
        return SleeveBCandidateBuildResult(market_data.symbol, None, "INSUFFICIENT_DAILY_DATA")
    if len(market_data.four_hour_bars) < max(cfg.donchian_lookback_bars + 1, cfg.atr_period + 1):
        return SleeveBCandidateBuildResult(market_data.symbol, None, "INSUFFICIENT_4H_DATA")
    if cfg.require_1h_timing and len(market_data.one_hour_bars) < max(cfg.one_hour_ema_period, cfg.atr_period + 1):
        return SleeveBCandidateBuildResult(market_data.symbol, None, "INSUFFICIENT_1H_DATA")

    daily_closes = [bar.close for bar in market_data.daily_bars]
    four_hour_closes = [bar.close for bar in market_data.four_hour_bars]
    four_hour_highs = [bar.high for bar in market_data.four_hour_bars]
    four_hour_lows = [bar.low for bar in market_data.four_hour_bars]
    regime = regime_from_daily_close(daily_closes)
    signal = donchian_signal(
        market_data.symbol,
        regime,
        four_hour_closes,
        four_hour_highs,
        four_hour_lows,
        cfg.donchian_lookback_bars,
    )
    if signal.side is None:
        return SleeveBCandidateBuildResult(market_data.symbol, None, signal.reason)

    timing = _one_hour_timing(signal.side, market_data.one_hour_bars, cfg) if cfg.require_1h_timing else "OK"
    if timing != "OK":
        return SleeveBCandidateBuildResult(market_data.symbol, None, timing)

    four_hour_entry_price = market_data.four_hour_bars[-1].close
    entry_price = _refined_entry_price(signal.side, four_hour_entry_price, market_data.one_hour_bars, cfg)
    atr_value = _atr(list(market_data.four_hour_bars), cfg.atr_period)
    stop_distance = atr_value * cfg.stop_atr_multiple
    if signal.side == PositionSide.LONG:
        stop_price = entry_price - stop_distance
    else:
        stop_price = entry_price + stop_distance

    candidate = SleeveBSignalCandidate(
        symbol=market_data.symbol,
        side=signal.side,
        entry_price=entry_price,
        stop_price=stop_price,
        setup_id=f"auto-{market_data.symbol.lower()}-{signal.reason.lower()[:16]}",
    )
    return SleeveBCandidateBuildResult(market_data.symbol, candidate, signal.reason)


def build_sleeve_b_candidates(
    market_data: list[SleeveBMarketData],
    config: SleeveBCandidateBuilderConfig | None = None,
) -> list[SleeveBCandidateBuildResult]:
    return [build_sleeve_b_candidate(item, config) for item in market_data]


def _one_hour_timing(side: PositionSide, one_hour_bars: tuple[OhlcBar, ...], cfg: SleeveBCandidateBuilderConfig) -> str:
    closes = [bar.close for bar in one_hour_bars]
    ema_value = ema(closes, cfg.one_hour_ema_period)[-1]
    last = one_hour_bars[-1]
    atr_value = _atr(list(one_hour_bars), cfg.atr_period)

    if side == PositionSide.LONG:
        if last.close < ema_value:
            return "ONE_HOUR_LONG_BELOW_EMA20"
        if _bearish_reversal(last):
            return "ONE_HOUR_LONG_BEARISH_REVERSAL"
        if last.close - ema_value > atr_value * cfg.max_1h_extension_atr:
            return "ONE_HOUR_LONG_OVEREXTENDED"
    else:
        if last.close > ema_value:
            return "ONE_HOUR_SHORT_ABOVE_EMA20"
        if _bullish_reversal(last):
            return "ONE_HOUR_SHORT_BULLISH_REVERSAL"
        if ema_value - last.close > atr_value * cfg.max_1h_extension_atr:
            return "ONE_HOUR_SHORT_OVEREXTENDED"
    return "OK"


def _refined_entry_price(
    side: PositionSide,
    four_hour_entry_price: Decimal,
    one_hour_bars: tuple[OhlcBar, ...],
    cfg: SleeveBCandidateBuilderConfig,
) -> Decimal:
    if not one_hour_bars:
        return four_hour_entry_price
    one_hour_close = one_hour_bars[-1].close
    offset = cfg.entry_offset_bps / Decimal("10000")
    if side == PositionSide.LONG:
        return min(four_hour_entry_price, one_hour_close * (Decimal("1") - offset))
    return max(four_hour_entry_price, one_hour_close * (Decimal("1") + offset))


def _bearish_reversal(bar: OhlcBar) -> bool:
    body = abs(bar.close - bar.open)
    range_size = bar.high - bar.low
    return bar.close < bar.open and range_size > 0 and body / range_size >= Decimal("0.7")


def _bullish_reversal(bar: OhlcBar) -> bool:
    body = abs(bar.close - bar.open)
    range_size = bar.high - bar.low
    return bar.close > bar.open and range_size > 0 and body / range_size >= Decimal("0.7")


def _atr(bars: list[OhlcBar], period: int) -> Decimal:
    if len(bars) < period + 1:
        raise ValueError("insufficient bars for ATR")
    true_ranges: list[Decimal] = []
    for index in range(len(bars) - period, len(bars)):
        current = bars[index]
        previous_close = bars[index - 1].close
        true_ranges.append(
            max(
                current.high - current.low,
                abs(current.high - previous_close),
                abs(current.low - previous_close),
            )
        )
    return sum(true_ranges, Decimal("0")) / Decimal(period)
