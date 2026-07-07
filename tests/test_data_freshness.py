from datetime import UTC, datetime, timedelta

from dual_sleeve_trader.core.models import DataPointFreshness
from dual_sleeve_trader.risk.data_freshness import DataFreshnessGate


def test_freshness_gate_reports_stale_points() -> None:
    now = datetime(2026, 7, 7, tzinfo=UTC)
    gate = DataFreshnessGate(
        [
            DataPointFreshness("mark_price", now - timedelta(seconds=2), 5),
            DataPointFreshness("orderbook", now - timedelta(seconds=3), 2),
        ]
    )
    report = gate.evaluate(now)
    assert not report.is_fresh
    assert report.stale_points == ("orderbook",)
