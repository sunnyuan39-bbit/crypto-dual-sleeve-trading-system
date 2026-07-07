from __future__ import annotations

import time
from dataclasses import dataclass

from dual_sleeve_trader.execution.reconciliation_runner import ReconciliationRunner, ReconciliationRunResult


@dataclass(frozen=True)
class PeriodicReconciliationConfig:
    interval_seconds: int = 30
    max_iterations: int | None = None
    stop_on_mismatch: bool = True


class PeriodicReconciliationLoop:
    def __init__(self, runner: ReconciliationRunner, config: PeriodicReconciliationConfig) -> None:
        self.runner = runner
        self.config = config

    def run(self) -> list[ReconciliationRunResult]:
        results: list[ReconciliationRunResult] = []
        iterations = 0
        while self.config.max_iterations is None or iterations < self.config.max_iterations:
            result = self.runner.run_once()
            results.append(result)
            iterations += 1

            if self.config.stop_on_mismatch and not result.report.consistent:
                break
            if self.config.max_iterations is not None and iterations >= self.config.max_iterations:
                break
            time.sleep(self.config.interval_seconds)
        return results
