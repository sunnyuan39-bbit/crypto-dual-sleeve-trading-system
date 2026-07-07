from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dual_sleeve_trader.config.runtime import RuntimeConfig
from dual_sleeve_trader.exchange.factory import build_exchange_adapter
from dual_sleeve_trader.execution.position_reconciliation import PositionReconciler, PositionReconciliationReport
from dual_sleeve_trader.execution.reconciliation import OrderReconciler, ReconciliationReport
from dual_sleeve_trader.execution.safe_mode import SafeModeController
from dual_sleeve_trader.ops.alerts import AlertSink, ConsoleAlertSink
from dual_sleeve_trader.storage.position_store import SQLitePositionStore
from dual_sleeve_trader.storage.sqlite_store import SQLiteOrderStore


@dataclass(frozen=True)
class DaemonConfig:
    interval_seconds: int = 30
    max_iterations: int | None = None
    stop_on_mismatch: bool = True
    refresh_positions_before_reconcile: bool = False


@dataclass(frozen=True)
class DaemonIterationResult:
    order_report: ReconciliationReport
    position_report: PositionReconciliationReport
    safe_mode_active: bool

    @property
    def consistent(self) -> bool:
        return self.order_report.consistent and self.position_report.consistent


class DaemonRunner:
    def __init__(
        self,
        order_reconciler: OrderReconciler,
        position_reconciler: PositionReconciler,
        safe_mode: SafeModeController,
        alerts: AlertSink,
        config: DaemonConfig,
    ) -> None:
        self.order_reconciler = order_reconciler
        self.position_reconciler = position_reconciler
        self.safe_mode = safe_mode
        self.alerts = alerts
        self.config = config

    def run_once(self) -> DaemonIterationResult:
        if self.config.refresh_positions_before_reconcile:
            self.position_reconciler.refresh_local_positions_from_exchange()

        order_report = self.order_reconciler.reconcile_open_orders()
        position_report = self.position_reconciler.reconcile_positions()
        result = DaemonIterationResult(
            order_report=order_report,
            position_report=position_report,
            safe_mode_active=not self.safe_mode.allows_new_entries,
        )
        if not result.consistent:
            self.alerts.send(_format_daemon_mismatch(result))
        return result

    def run(self) -> list[DaemonIterationResult]:
        results: list[DaemonIterationResult] = []
        iterations = 0
        while self.config.max_iterations is None or iterations < self.config.max_iterations:
            result = self.run_once()
            results.append(result)
            iterations += 1
            if self.config.stop_on_mismatch and not result.consistent:
                break
            if self.config.max_iterations is not None and iterations >= self.config.max_iterations:
                break
            time.sleep(self.config.interval_seconds)
        return results


def build_daemon_runner(
    runtime: RuntimeConfig,
    config: DaemonConfig | None = None,
    alerts: AlertSink | None = None,
    allow_inert_fallback: bool = True,
) -> DaemonRunner:
    daemon_config = config or DaemonConfig()
    alert_sink = alerts or ConsoleAlertSink()
    safe_mode = SafeModeController()
    exchange = build_exchange_adapter(runtime, allow_inert_fallback=allow_inert_fallback)
    db_path = Path(runtime.state_db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True) if db_path.parent != Path(".") else None
    order_store = SQLiteOrderStore(db_path)
    position_store = SQLitePositionStore(db_path)
    order_reconciler = OrderReconciler(order_store, exchange, safe_mode)
    position_reconciler = PositionReconciler(position_store, exchange, safe_mode)
    return DaemonRunner(order_reconciler, position_reconciler, safe_mode, alert_sink, daemon_config)


def daemon_result_to_dict(result: DaemonIterationResult) -> dict[str, Any]:
    return {
        "consistent": result.consistent,
        "safe_mode_active": result.safe_mode_active,
        "order_consistent": result.order_report.consistent,
        "position_consistent": result.position_report.consistent,
        "order_error": result.order_report.error,
        "position_error": result.position_report.error,
        "order_missing_on_exchange": result.order_report.missing_on_exchange,
        "order_unknown_on_local": result.order_report.unknown_on_local,
        "position_missing_on_exchange": result.position_report.missing_on_exchange,
        "position_unknown_on_local": result.position_report.unknown_on_local,
        "position_amount_mismatches": result.position_report.amount_mismatches,
    }


def _format_daemon_mismatch(result: DaemonIterationResult) -> str:
    return (
        "DAEMON_RECONCILIATION_MISMATCH "
        f"order_consistent={result.order_report.consistent} "
        f"position_consistent={result.position_report.consistent} "
        f"safe_mode={result.safe_mode_active}"
    )
