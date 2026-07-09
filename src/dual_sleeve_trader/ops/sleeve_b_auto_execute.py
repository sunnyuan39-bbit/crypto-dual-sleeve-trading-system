from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Protocol

from dual_sleeve_trader.config.runtime import ExchangeName, RuntimeConfig
from dual_sleeve_trader.core.enums import TradingMode
from dual_sleeve_trader.execution.position_reconciliation import PositionReconciler, PositionReconciliationReport
from dual_sleeve_trader.execution.reconciliation import OrderReconciler, ReconciliationReport
from dual_sleeve_trader.execution.safe_mode import SafeModeController
from dual_sleeve_trader.execution.sleeve_b_testnet_loop import (
    SleeveBAutoLoopConfig,
    SleeveBAutoLoopRunResult,
    SleeveBAutoTestnetLoop,
)
from dual_sleeve_trader.exchange.factory import build_exchange_adapter
from dual_sleeve_trader.storage.position_store import SQLitePositionStore
from dual_sleeve_trader.storage.sqlite_store import SQLiteOrderStore
from dual_sleeve_trader.strategies.sleeve_b_candidate_builder import (
    SleeveBMarketData,
    build_sleeve_b_candidates,
)
from dual_sleeve_trader.strategies.sleeve_b_replay import OhlcBar


class SleeveBAutoExecuteSafetyError(RuntimeError):
    pass


class SleeveBAutoExecuteExchange(Protocol):
    def fetch_klines(self, symbol: str, interval: str, limit: int = 500) -> list[OhlcBar]: ...


@dataclass(frozen=True)
class SleeveBAutoExecuteConfig:
    symbols: tuple[str, ...] = ("BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "HYPEUSDT")
    daily_limit: int = 250
    four_hour_limit: int = 150
    one_hour_limit: int = 100
    max_new_orders_per_run: int = 1
    acknowledge_testnet_order: bool = False


@dataclass(frozen=True)
class SleeveBAutoExecuteResult:
    loop_result: SleeveBAutoLoopRunResult
    order_reconciliation: ReconciliationReport
    position_reconciliation: PositionReconciliationReport
    candidates_scanned: int

    @property
    def ok(self) -> bool:
        return (
            self.order_reconciliation.consistent
            and self.position_reconciliation.consistent
            and not self.loop_result.safe_mode_active
        )


def run_sleeve_b_auto_execute(
    runtime: RuntimeConfig,
    config: SleeveBAutoExecuteConfig,
) -> SleeveBAutoExecuteResult:
    _validate_runtime(runtime)
    if not config.acknowledge_testnet_order:
        raise SleeveBAutoExecuteSafetyError("explicit acknowledgement is required before placing a testnet order")

    exchange = build_exchange_adapter(runtime, allow_inert_fallback=False)
    order_store = SQLiteOrderStore(runtime.state_db_path)
    position_store = SQLitePositionStore(runtime.state_db_path)
    safe_mode = SafeModeController()

    market_data = _fetch_market_data(exchange, config)
    candidate_results = build_sleeve_b_candidates(market_data)
    candidates = [result.candidate for result in candidate_results if result.candidate is not None]

    loop = SleeveBAutoTestnetLoop(
        exchange,
        order_store,
        safe_mode,
        config=SleeveBAutoLoopConfig(
            require_ack=True,
            max_new_orders_per_run=config.max_new_orders_per_run,
        ),
    )
    loop_result = loop.run_once(candidates)

    order_report = OrderReconciler(order_store, exchange, safe_mode).reconcile_open_orders()
    position_reconciler = PositionReconciler(position_store, exchange, safe_mode)
    position_reconciler.refresh_local_positions_from_exchange()
    position_report = position_reconciler.reconcile_positions()

    return SleeveBAutoExecuteResult(
        loop_result=loop_result,
        order_reconciliation=order_report,
        position_reconciliation=position_report,
        candidates_scanned=len(candidate_results),
    )


def result_to_dict(result: SleeveBAutoExecuteResult) -> dict[str, Any]:
    return {
        "ok": result.ok,
        "candidates_scanned": result.candidates_scanned,
        "submitted_orders": result.loop_result.submitted_orders,
        "safe_mode_active": result.loop_result.safe_mode_active,
        "decisions": [
            {
                "symbol": decision.symbol,
                "accepted": decision.accepted,
                "reason": decision.reason,
                "allocation_reason": decision.allocation.reason,
                "quantity": str(decision.allocation.quantity),
                "entry_price": str(decision.allocation.entry_price),
                "notional": str(decision.allocation.notional),
                "initial_margin": str(decision.allocation.initial_margin),
                "route_reason": None if decision.route_result is None else decision.route_result.reason,
                "client_order_id": None
                if decision.route_result is None or decision.route_result.order is None
                else decision.route_result.order.client_order_id,
                "exchange_order_id": None
                if decision.route_result is None or decision.route_result.order is None
                else decision.route_result.order.exchange_order_id,
            }
            for decision in result.loop_result.decisions
        ],
        "order_reconciliation": {
            "consistent": result.order_reconciliation.consistent,
            "missing_on_exchange": list(result.order_reconciliation.missing_on_exchange),
            "unknown_on_local": list(result.order_reconciliation.unknown_on_local),
            "status_mismatches": list(result.order_reconciliation.status_mismatches),
            "error": result.order_reconciliation.error,
        },
        "position_reconciliation": {
            "consistent": result.position_reconciliation.consistent,
            "missing_on_exchange": [list(item) for item in result.position_reconciliation.missing_on_exchange],
            "unknown_on_local": [list(item) for item in result.position_reconciliation.unknown_on_local],
            "amount_mismatches": [list(item) for item in result.position_reconciliation.amount_mismatches],
            "error": result.position_reconciliation.error,
        },
    }


def _fetch_market_data(exchange: SleeveBAutoExecuteExchange, config: SleeveBAutoExecuteConfig) -> list[SleeveBMarketData]:
    return [
        SleeveBMarketData(
            symbol=symbol,
            daily_bars=tuple(exchange.fetch_klines(symbol, "1d", config.daily_limit)),
            four_hour_bars=tuple(exchange.fetch_klines(symbol, "4h", config.four_hour_limit)),
            one_hour_bars=tuple(exchange.fetch_klines(symbol, "1h", config.one_hour_limit)),
        )
        for symbol in config.symbols
    ]


def _validate_runtime(runtime: RuntimeConfig) -> None:
    if runtime.trading_mode != TradingMode.EXCHANGE_TESTNET:
        raise SleeveBAutoExecuteSafetyError("TRADING_MODE must be EXCHANGE_TESTNET")
    if runtime.exchange != ExchangeName.BINANCE_USDM_TESTNET:
        raise SleeveBAutoExecuteSafetyError("EXCHANGE must be BINANCE_USDM_TESTNET")
    if not runtime.has_credentials:
        raise SleeveBAutoExecuteSafetyError("testnet credentials are required")
