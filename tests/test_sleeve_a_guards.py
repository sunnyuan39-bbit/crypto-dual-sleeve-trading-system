from decimal import Decimal

from dual_sleeve_trader.risk.borrow_stress import (
    BorrowConfidence,
    BorrowStatus,
    SqueezeRisk,
    borrow_stress_score,
    squeeze_risk_level,
)
from dual_sleeve_trader.risk.capacity import CapacitySnapshot, capacity_check
from dual_sleeve_trader.strategies.sleeve_a_scanner import oi_from_peak_usd, price_falling


def test_capacity_checks_exit_ask_depth() -> None:
    snapshot = CapacitySnapshot(
        open_interest_usd=Decimal("10000000"),
        volume_24h_usd=Decimal("10000000"),
        entry_bid_depth_usd=Decimal("100000"),
        exit_ask_depth_usd=Decimal("1000"),
    )
    assert not capacity_check(Decimal("10000"), snapshot)


def test_price_falling_by_24h_return() -> None:
    closes = [Decimal("100"), Decimal("100"), Decimal("100"), Decimal("100"), Decimal("100"), Decimal("100"), Decimal("91")]
    lows = [Decimal("100"), Decimal("99"), Decimal("98")]
    assert price_falling(closes, lows)


def test_oi_from_peak_usd() -> None:
    oi = [Decimal("100")] * 179 + [Decimal("80")]
    assert oi_from_peak_usd(oi) == Decimal("-0.2")


def test_low_confidence_deep_funding_is_at_least_high() -> None:
    status = BorrowStatus(
        is_borrow_supported=True,
        max_borrowable_base=None,
        max_borrowable_usd=None,
        borrow_rate_annualized=None,
        confidence=BorrowConfidence.LOW,
    )
    stress = borrow_stress_score(status, Decimal("10000"))
    level = squeeze_risk_level(Decimal("-0.0011"), stress)
    assert level == SqueezeRisk.HIGH
