from decimal import Decimal

from dual_sleeve_trader.core.enums import PositionSide
from dual_sleeve_trader.strategies.sleeve_b_candidate_builder import SleeveBMarketData, build_sleeve_b_candidate
from dual_sleeve_trader.strategies.sleeve_b_replay import OhlcBar


def _bar(timestamp: str, close: str, high: str | None = None, low: str | None = None, open_: str | None = None) -> OhlcBar:
    close_decimal = Decimal(close)
    return OhlcBar(
        timestamp=timestamp,
        open=Decimal(open_) if open_ is not None else close_decimal,
        high=Decimal(high) if high is not None else close_decimal + Decimal("1"),
        low=Decimal(low) if low is not None else close_decimal - Decimal("1"),
        close=close_decimal,
    )


def _daily() -> tuple[OhlcBar, ...]:
    return tuple(_bar(f"2023-D{day:03d}", str(100 + day)) for day in range(1, 221))


def _four_hour_breakout() -> tuple[OhlcBar, ...]:
    return tuple([_bar(f"2024-B{index:03d}", "100", "101", "99") for index in range(121)] + [_bar("2024-B121", "105", "106", "104")])


def test_1h_timing_rejects_long_below_ema20() -> None:
    one_hour = tuple([_bar(f"2024-H{index:03d}", "110", "111", "109") for index in range(99)] + [_bar("2024-H099", "90", "100", "89")])

    result = build_sleeve_b_candidate(SleeveBMarketData("BTCUSDT", _daily(), _four_hour_breakout(), one_hour))

    assert result.candidate is None
    assert result.reason == "ONE_HOUR_LONG_BELOW_EMA20"


def test_1h_timing_rejects_long_bearish_reversal() -> None:
    one_hour = tuple([_bar(f"2024-H{index:03d}", "104", "105", "103") for index in range(99)] + [_bar("2024-H099", "104", "111", "103", open_="110")])

    result = build_sleeve_b_candidate(SleeveBMarketData("BTCUSDT", _daily(), _four_hour_breakout(), one_hour))

    assert result.candidate is None
    assert result.reason == "ONE_HOUR_LONG_BEARISH_REVERSAL"


def test_1h_timing_refines_long_entry_price() -> None:
    one_hour = tuple(_bar(f"2024-H{index:03d}", "104", "105", "103") for index in range(100))

    result = build_sleeve_b_candidate(SleeveBMarketData("BTCUSDT", _daily(), _four_hour_breakout(), one_hour))

    assert result.candidate is not None
    assert result.candidate.side == PositionSide.LONG
    assert result.candidate.entry_price < Decimal("105")
