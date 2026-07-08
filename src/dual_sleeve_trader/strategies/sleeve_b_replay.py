from __future__ import annotations

import csv
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from dual_sleeve_trader.core.enums import PositionSide
from dual_sleeve_trader.strategies.sleeve_b import donchian_signal, regime_from_daily_close


@dataclass(frozen=True)
class OhlcBar:
    timestamp: str
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal


@dataclass(frozen=True)
class SleeveBReplayConfig:
    unit_r: Decimal = Decimal("800")
    sleeve_equity: Decimal = Decimal("80000")
    max_leverage: Decimal = Decimal("5")
    donchian_lookback_bars: int = 120
    atr_period: int = 14
    stop_atr_multiple: Decimal = Decimal("2.5")
    tp1_r: Decimal = Decimal("1.5")
    tp2_r: Decimal = Decimal("2.5")
    tp3_r: Decimal = Decimal("4")
    tp1_fraction: Decimal = Decimal("0.3")
    tp2_fraction: Decimal = Decimal("0.3")
    time_stop_bars: int = 12

    @property
    def tp3_fraction(self) -> Decimal:
        return Decimal("1") - self.tp1_fraction - self.tp2_fraction


@dataclass(frozen=True)
class SleeveBTrade:
    symbol: str
    side: PositionSide
    entry_time: str
    entry_price: Decimal
    initial_stop: Decimal
    quantity: Decimal
    notional: Decimal
    exit_time: str
    exit_price: Decimal
    exit_reason: str
    realized_pnl: Decimal
    gross_r: Decimal
    bars_held: int
    tp_hits: tuple[str, ...]


@dataclass(frozen=True)
class SleeveBReplaySummary:
    symbol: str
    trades: int
    wins: int
    losses: int
    total_pnl: Decimal
    total_r: Decimal
    max_drawdown: Decimal


@dataclass(frozen=True)
class SleeveBReplayResult:
    symbol: str
    trades: tuple[SleeveBTrade, ...]
    summary: SleeveBReplaySummary


def load_ohlc_csv(path: str | Path) -> list[OhlcBar]:
    with Path(path).open(newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        return [
            OhlcBar(
                timestamp=str(row["timestamp"]),
                open=Decimal(str(row["open"])),
                high=Decimal(str(row["high"])),
                low=Decimal(str(row["low"])),
                close=Decimal(str(row["close"])),
            )
            for row in reader
        ]


def run_sleeve_b_replay(
    symbol: str,
    daily_bars: list[OhlcBar],
    four_hour_bars: list[OhlcBar],
    config: SleeveBReplayConfig | None = None,
) -> SleeveBReplayResult:
    cfg = config or SleeveBReplayConfig()
    trades: list[SleeveBTrade] = []
    index = max(cfg.donchian_lookback_bars + 1, cfg.atr_period + 1)

    while index < len(four_hour_bars):
        bar = four_hour_bars[index]
        daily_closes = _daily_closes_until(daily_bars, bar.timestamp)
        regime = regime_from_daily_close(daily_closes)
        signal = donchian_signal(
            symbol,
            regime,
            [item.close for item in four_hour_bars[: index + 1]],
            [item.high for item in four_hour_bars[: index + 1]],
            [item.low for item in four_hour_bars[: index + 1]],
            cfg.donchian_lookback_bars,
        )
        if signal.side is None:
            index += 1
            continue

        trade = _simulate_trade(symbol, signal.side, four_hour_bars, index, cfg)
        trades.append(trade)
        index += max(trade.bars_held, 1)

    return SleeveBReplayResult(symbol=symbol, trades=tuple(trades), summary=_summarize(symbol, trades))


def _simulate_trade(
    symbol: str,
    side: PositionSide,
    bars: list[OhlcBar],
    entry_index: int,
    cfg: SleeveBReplayConfig,
) -> SleeveBTrade:
    entry_bar = bars[entry_index]
    entry = entry_bar.close
    atr_value = _atr(bars[: entry_index + 1], cfg.atr_period)
    stop_distance = atr_value * cfg.stop_atr_multiple
    if stop_distance <= 0:
        raise ValueError("stop distance must be positive")

    if side == PositionSide.LONG:
        initial_stop = entry - stop_distance
        tps = (
            ("TP1", entry + cfg.tp1_r * stop_distance, cfg.tp1_fraction),
            ("TP2", entry + cfg.tp2_r * stop_distance, cfg.tp2_fraction),
            ("TP3", entry + cfg.tp3_r * stop_distance, cfg.tp3_fraction),
        )
    else:
        initial_stop = entry + stop_distance
        tps = (
            ("TP1", entry - cfg.tp1_r * stop_distance, cfg.tp1_fraction),
            ("TP2", entry - cfg.tp2_r * stop_distance, cfg.tp2_fraction),
            ("TP3", entry - cfg.tp3_r * stop_distance, cfg.tp3_fraction),
        )

    max_notional = cfg.sleeve_equity * cfg.max_leverage
    quantity = min(cfg.unit_r / stop_distance, max_notional / entry)
    notional = quantity * entry
    remaining_fraction = Decimal("1")
    realized = Decimal("0")
    stop = initial_stop
    tp_hits: list[str] = []
    exit_price = entry
    exit_reason = "TIME_STOP"
    exit_time = entry_bar.timestamp
    bars_held = 0

    for offset, bar in enumerate(bars[entry_index + 1 :], start=1):
        bars_held = offset
        exit_time = bar.timestamp

        if _stop_hit(side, bar, stop):
            realized += _pnl(side, entry, stop, quantity * remaining_fraction)
            exit_price = stop
            exit_reason = "STOP_LOSS" if stop == initial_stop else "BREAKEVEN_STOP"
            remaining_fraction = Decimal("0")
            break

        for label, price, fraction in tps:
            if label in tp_hits:
                continue
            if _target_hit(side, bar, price):
                close_fraction = min(fraction, remaining_fraction)
                realized += _pnl(side, entry, price, quantity * close_fraction)
                remaining_fraction -= close_fraction
                tp_hits.append(label)
                if label == "TP1":
                    stop = entry
                exit_price = price
                exit_reason = label

        if remaining_fraction <= 0:
            break

        if offset >= cfg.time_stop_bars:
            realized += _pnl(side, entry, bar.close, quantity * remaining_fraction)
            exit_price = bar.close
            exit_reason = "TIME_STOP"
            remaining_fraction = Decimal("0")
            break

    if remaining_fraction > 0:
        last_bar = bars[-1]
        bars_held = max(len(bars) - entry_index - 1, 0)
        exit_time = last_bar.timestamp
        exit_price = last_bar.close
        exit_reason = "END_OF_DATA"
        realized += _pnl(side, entry, exit_price, quantity * remaining_fraction)

    return SleeveBTrade(
        symbol=symbol,
        side=side,
        entry_time=entry_bar.timestamp,
        entry_price=entry,
        initial_stop=initial_stop,
        quantity=quantity,
        notional=notional,
        exit_time=exit_time,
        exit_price=exit_price,
        exit_reason=exit_reason,
        realized_pnl=realized,
        gross_r=realized / cfg.unit_r,
        bars_held=bars_held,
        tp_hits=tuple(tp_hits),
    )


def _daily_closes_until(daily_bars: list[OhlcBar], timestamp: str) -> list[Decimal]:
    return [bar.close for bar in daily_bars if bar.timestamp <= timestamp]


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


def _target_hit(side: PositionSide, bar: OhlcBar, price: Decimal) -> bool:
    if side == PositionSide.LONG:
        return bar.high >= price
    return bar.low <= price


def _stop_hit(side: PositionSide, bar: OhlcBar, price: Decimal) -> bool:
    if side == PositionSide.LONG:
        return bar.low <= price
    return bar.high >= price


def _pnl(side: PositionSide, entry: Decimal, exit_price: Decimal, quantity: Decimal) -> Decimal:
    if side == PositionSide.LONG:
        return (exit_price - entry) * quantity
    return (entry - exit_price) * quantity


def _summarize(symbol: str, trades: list[SleeveBTrade]) -> SleeveBReplaySummary:
    equity_curve: list[Decimal] = []
    running = Decimal("0")
    for trade in trades:
        running += trade.realized_pnl
        equity_curve.append(running)

    peak = Decimal("0")
    max_drawdown = Decimal("0")
    for value in equity_curve:
        peak = max(peak, value)
        max_drawdown = min(max_drawdown, value - peak)

    return SleeveBReplaySummary(
        symbol=symbol,
        trades=len(trades),
        wins=sum(1 for trade in trades if trade.realized_pnl > 0),
        losses=sum(1 for trade in trades if trade.realized_pnl <= 0),
        total_pnl=sum((trade.realized_pnl for trade in trades), Decimal("0")),
        total_r=sum((trade.gross_r for trade in trades), Decimal("0")),
        max_drawdown=max_drawdown,
    )
