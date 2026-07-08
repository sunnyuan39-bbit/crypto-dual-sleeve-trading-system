from decimal import Decimal

from dual_sleeve_trader.core.enums import PositionSide
from dual_sleeve_trader.strategies.sleeve_b_replay import (
    OhlcBar,
    SleeveBReplayConfig,
    load_ohlc_csv,
    run_sleeve_b_replay,
)


def _bar(timestamp: str, close: str, high: str | None = None, low: str | None = None) -> OhlcBar:
    close_decimal = Decimal(close)
    return OhlcBar(
        timestamp=timestamp,
        open=close_decimal,
        high=Decimal(high) if high is not None else close_decimal + Decimal("1"),
        low=Decimal(low) if low is not None else close_decimal - Decimal("1"),
        close=close_decimal,
    )


def _bull_daily_bars() -> list[OhlcBar]:
    return [_bar(f"2024-01-{day:02d}", str(100 + day)) for day in range(1, 221)]


def _bear_daily_bars() -> list[OhlcBar]:
    return [_bar(f"2024-01-{day:02d}", str(400 - day)) for day in range(1, 221)]


def test_sleeve_b_replay_long_breakout_hits_tp3() -> None:
    daily = _bull_daily_bars()
    four_hour = [_bar(f"2024-01-01T{index:02d}:00:00", "100", "101", "99") for index in range(121)]
    four_hour.append(_bar("2024-01-10T00:00:00", "105", "106", "104"))
    four_hour.append(_bar("2024-01-10T04:00:00", "124", "126", "104"))

    result = run_sleeve_b_replay(
        "BTCUSDT",
        daily,
        four_hour,
        SleeveBReplayConfig(donchian_lookback_bars=20, atr_period=14),
    )

    assert result.summary.trades >= 1
    trade = result.trades[0]
    assert trade.side == PositionSide.LONG
    assert trade.exit_reason == "TP3"
    assert trade.tp_hits == ("TP1", "TP2", "TP3")
    assert trade.realized_pnl > 0


def test_sleeve_b_replay_short_breakdown_hits_tp1_then_breakeven() -> None:
    daily = _bear_daily_bars()
    four_hour = [_bar(f"2024-01-01T{index:02d}:00:00", "200", "201", "199") for index in range(121)]
    four_hour.append(_bar("2024-01-10T00:00:00", "195", "196", "194"))
    four_hour.append(_bar("2024-01-10T04:00:00", "191", "195", "187"))

    result = run_sleeve_b_replay(
        "ETHUSDT",
        daily,
        four_hour,
        SleeveBReplayConfig(donchian_lookback_bars=20, atr_period=14),
    )

    trade = result.trades[0]
    assert trade.side == PositionSide.SHORT
    assert trade.tp_hits[0] == "TP1"
    assert trade.exit_reason in {"BREAKEVEN_STOP", "TP2", "TP3"}


def test_sleeve_b_replay_time_stop_when_targets_not_hit() -> None:
    daily = _bull_daily_bars()
    four_hour = [_bar(f"2024-01-01T{index:02d}:00:00", "100", "101", "99") for index in range(121)]
    four_hour.append(_bar("2024-01-10T00:00:00", "105", "106", "104"))
    four_hour.extend(
        _bar(f"2024-01-10T{hour:02d}:00:00", "106", "107", "104")
        for hour in range(4, 56, 4)
    )

    result = run_sleeve_b_replay(
        "SOLUSDT",
        daily,
        four_hour,
        SleeveBReplayConfig(donchian_lookback_bars=20, atr_period=14, time_stop_bars=3),
    )

    assert result.trades[0].exit_reason == "TIME_STOP"
    assert result.trades[0].bars_held == 3


def test_load_ohlc_csv(tmp_path) -> None:
    csv_path = tmp_path / "bars.csv"
    csv_path.write_text(
        "timestamp,open,high,low,close\n"
        "2024-01-01,1,2,0.5,1.5\n",
        encoding="utf-8",
    )

    bars = load_ohlc_csv(csv_path)

    assert bars == [OhlcBar("2024-01-01", Decimal("1"), Decimal("2"), Decimal("0.5"), Decimal("1.5"))]
