from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from dual_sleeve_trader.core.models import DataPointFreshness


@dataclass(frozen=True)
class FreshnessReport:
    is_fresh: bool
    stale_points: tuple[str, ...]


class DataFreshnessGate:
    def __init__(self, required_points: list[DataPointFreshness]) -> None:
        self.required_points = required_points

    def evaluate(self, now: datetime | None = None) -> FreshnessReport:
        stale = tuple(point.name for point in self.required_points if not point.is_fresh(now))
        return FreshnessReport(is_fresh=not stale, stale_points=stale)
