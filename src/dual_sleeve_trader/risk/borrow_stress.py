from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum


class BorrowConfidence(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class SqueezeRisk(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    EXTREME = "EXTREME"


@dataclass(frozen=True)
class BorrowStatus:
    is_borrow_supported: bool | None
    max_borrowable_base: Decimal | None
    max_borrowable_usd: Decimal | None
    borrow_rate_annualized: Decimal | None
    data_scope: str = "account_level_proxy"
    confidence: BorrowConfidence = BorrowConfidence.LOW
    zero_reason: str | None = None


@dataclass(frozen=True)
class BorrowStressResult:
    score: int
    confidence: BorrowConfidence


def borrow_stress_score(status: BorrowStatus, planned_notional: Decimal) -> BorrowStressResult:
    score = 0
    confidence = status.confidence

    if status.is_borrow_supported is False:
        score += 3

    mb = status.max_borrowable_usd
    if mb is not None:
        ratio = mb / planned_notional if planned_notional > 0 else Decimal("0")
        if ratio < Decimal("1"):
            score += 3
        elif ratio < Decimal("2"):
            score += 2
        elif ratio < Decimal("5"):
            score += 1
        if mb < Decimal("50000"):
            score += 1

    if status.max_borrowable_base == 0:
        if status.zero_reason in {"pool_likely_empty", "unsupported_asset"}:
            score += 3
        else:
            score += 1
            confidence = BorrowConfidence.LOW

    rate = status.borrow_rate_annualized
    if rate is not None:
        if rate > Decimal("100"):
            score += 2
        elif rate > Decimal("50"):
            score += 1

    return BorrowStressResult(score=score, confidence=confidence)


def squeeze_risk_level(
    funding_8h: Decimal,
    stress: BorrowStressResult,
    funding_deep: Decimal = Decimal("-0.001"),
    funding_mild: Decimal = Decimal("-0.0005"),
    stress_veto: int = 5,
    stress_half_lo: int = 3,
) -> SqueezeRisk:
    if funding_8h < funding_deep and stress.score >= stress_veto:
        level = SqueezeRisk.EXTREME
    elif funding_8h < funding_deep and stress.score >= stress_half_lo:
        level = SqueezeRisk.HIGH
    elif funding_deep <= funding_8h < funding_mild:
        level = SqueezeRisk.MEDIUM
    else:
        level = SqueezeRisk.LOW

    if stress.confidence == BorrowConfidence.LOW and level == SqueezeRisk.LOW:
        level = SqueezeRisk.MEDIUM
    if stress.confidence == BorrowConfidence.LOW and funding_8h < funding_deep and level == SqueezeRisk.MEDIUM:
        level = SqueezeRisk.HIGH
    return level
