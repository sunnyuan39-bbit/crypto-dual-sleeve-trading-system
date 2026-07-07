from __future__ import annotations

from dataclasses import dataclass

from dual_sleeve_trader.execution.reconciliation import OrderReconciler, ReconciliationReport
from dual_sleeve_trader.ops.alerts import AlertSink


@dataclass(frozen=True)
class ReconciliationRunResult:
    report: ReconciliationReport
    alerted: bool


class ReconciliationRunner:
    def __init__(self, reconciler: OrderReconciler, alerts: AlertSink) -> None:
        self.reconciler = reconciler
        self.alerts = alerts

    def run_once(self) -> ReconciliationRunResult:
        report = self.reconciler.reconcile_open_orders()
        alerted = False
        if not report.consistent:
            self.alerts.send(
                "RECONCILIATION_MISMATCH "
                f"missing={report.missing_on_exchange} "
                f"unknown={report.unknown_on_local} "
                f"status={report.status_mismatches} "
                f"error={report.error}"
            )
            alerted = True
        return ReconciliationRunResult(report=report, alerted=alerted)
