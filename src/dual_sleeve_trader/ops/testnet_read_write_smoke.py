from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Protocol

from dual_sleeve_trader.config.runtime import ExchangeName, RuntimeConfig
from dual_sleeve_trader.core.account import AccountSnapshotV3, ExchangePositionSnapshot
from dual_sleeve_trader.core.enums import OrderAction, OrderSide, OrderStatus, OrderType, PositionSide, SleeveId, TradingMode
from dual_sleeve_trader.core.exchange_order import ExchangeOrderSnapshot
from dual_sleeve_trader.core.models import OrderIntent, OrderRecord, SymbolFilters
from dual_sleeve_trader.exchange.factory import build_exchange_adapter
from dual_sleeve_trader.execution.order_router import OrderRouter
from dual_sleeve_trader.execution.position_reconciliation import PositionReconciler, PositionReconciliationReport
from dual_sleeve_trader.execution.reconciliation import OrderReconciler, ReconciliationReport
from dual_sleeve_trader.execution.safe_mode import SafeModeController
from dual_sleeve_trader.storage.position_store import SQLitePositionStore
from dual_sleeve_trader.storage.sqlite_store import SQLiteOrderStore


class TestnetSmokeSafetyError(RuntimeError):
    pass


class ReadWriteSmokeExchange(Protocol):
    def get_symbol_filters(self, symbol: str) -> SymbolFilters: ...
    def fetch_account_snapshot(self) -> AccountSnapshotV3: ...
    def fetch_position_snapshots(self, symbol: str | None = None) -> list[ExchangePositionSnapshot]: ...
    def submit_order(self, order: OrderRecord) -> OrderRecord: ...
    def query_order(self, symbol: str, client_order_id: str) -> ExchangeOrderSnapshot | None: ...
    def cancel_order(self, client_order_id: str, symbol: str) -> OrderRecord | None: ...
    def fetch_open_orders(self) -> list[OrderRecord]: ...


@dataclass(frozen=True)
class TestnetSmokeOrderConfig:
    symbol: str
    side: OrderSide
    quantity: Decimal
    limit_price: Decimal
    setup_id: str = "smoke010"
    non_marketable_margin: Decimal = Decimal("0.2")
    require_non_marketable: bool = True


@dataclass(frozen=True)
class TestnetReadWriteSmokeResult:
    symbol: str
    client_order_id: str
    exchange_order_id: str | None
    submitted_status: OrderStatus
    queried_status_before_cancel: OrderStatus
    queried_status_after_cancel: OrderStatus
    order_reconciliation_consistent: bool
    position_reconciliation_consistent: bool
    safe_mode_active: bool
    account_total_wallet_balance: Decimal
    position_count: int

    @property
    def ok(self) -> bool:
        return (
            self.submitted_status in {OrderStatus.SUBMITTED, OrderStatus.PARTIALLY_FILLED, OrderStatus.FILLED}
            and self.queried_status_after_cancel == OrderStatus.CANCELED
            and self.order_reconciliation_consistent
            and self.position_reconciliation_consistent
            and not self.safe_mode_active
        )


def run_testnet_read_write_smoke(
    runtime: RuntimeConfig,
    order_config: TestnetSmokeOrderConfig,
    acknowledge_testnet_order: bool,
) -> TestnetReadWriteSmokeResult:
    _validate_runtime(runtime)
    if not acknowledge_testnet_order:
        raise TestnetSmokeSafetyError("explicit acknowledgement is required before placing a testnet order")
    exchange = build_exchange_adapter(runtime, allow_inert_fallback=False)
    return run_testnet_read_write_smoke_with_exchange(exchange, order_config, acknowledge_testnet_order)


def run_testnet_read_write_smoke_with_exchange(
    exchange: ReadWriteSmokeExchange,
    order_config: TestnetSmokeOrderConfig,
    acknowledge_testnet_order: bool,
) -> TestnetReadWriteSmokeResult:
    if not acknowledge_testnet_order:
        raise TestnetSmokeSafetyError("explicit acknowledgement is required before placing a testnet order")

    filters = exchange.get_symbol_filters(order_config.symbol)
    account = exchange.fetch_account_snapshot()
    positions = exchange.fetch_position_snapshots(order_config.symbol)
    _validate_non_marketable(order_config, positions)

    safe_mode = SafeModeController()
    router = OrderRouter(TradingMode.EXCHANGE_TESTNET, exchange, safe_mode)
    intent = OrderIntent(
        sleeve_id=SleeveId.B,
        symbol=order_config.symbol,
        side=order_config.side,
        order_type=OrderType.LIMIT,
        action=OrderAction.ENTRY,
        quantity=order_config.quantity,
        price=order_config.limit_price,
        reduce_only=False,
        setup_id=order_config.setup_id,
        metadata={"smoke_test": "PR-010"},
    )

    submitted_order: OrderRecord | None = None
    query_before: ExchangeOrderSnapshot | None = None
    query_after: ExchangeOrderSnapshot | None = None
    try:
        route_result = router.route(intent)
        if not route_result.accepted or route_result.order is None:
            raise TestnetSmokeSafetyError(f"testnet smoke order rejected: {route_result.reason}")
        submitted_order = route_result.order
        query_before = exchange.query_order(order_config.symbol, submitted_order.client_order_id)
    finally:
        if submitted_order is not None:
            exchange.cancel_order(submitted_order.client_order_id, order_config.symbol)
            query_after = exchange.query_order(order_config.symbol, submitted_order.client_order_id)

    if submitted_order is None or query_before is None or query_after is None:
        raise TestnetSmokeSafetyError("testnet smoke order lifecycle did not complete")

    order_report, position_report = _run_reconciliation(exchange, safe_mode)
    return TestnetReadWriteSmokeResult(
        symbol=order_config.symbol,
        client_order_id=submitted_order.client_order_id,
        exchange_order_id=submitted_order.exchange_order_id,
        submitted_status=submitted_order.status,
        queried_status_before_cancel=query_before.status,
        queried_status_after_cancel=query_after.status,
        order_reconciliation_consistent=order_report.consistent,
        position_reconciliation_consistent=position_report.consistent,
        safe_mode_active=not safe_mode.allows_new_entries,
        account_total_wallet_balance=account.total_wallet_balance,
        position_count=len(positions),
    )


def result_to_dict(result: TestnetReadWriteSmokeResult) -> dict[str, Any]:
    return {
        "ok": result.ok,
        "symbol": result.symbol,
        "client_order_id": result.client_order_id,
        "exchange_order_id": result.exchange_order_id,
        "submitted_status": result.submitted_status.value,
        "queried_status_before_cancel": result.queried_status_before_cancel.value,
        "queried_status_after_cancel": result.queried_status_after_cancel.value,
        "order_reconciliation_consistent": result.order_reconciliation_consistent,
        "position_reconciliation_consistent": result.position_reconciliation_consistent,
        "safe_mode_active": result.safe_mode_active,
        "account_total_wallet_balance": str(result.account_total_wallet_balance),
        "position_count": result.position_count,
    }


def _validate_runtime(runtime: RuntimeConfig) -> None:
    if runtime.trading_mode != TradingMode.EXCHANGE_TESTNET:
        raise TestnetSmokeSafetyError("TRADING_MODE must be EXCHANGE_TESTNET")
    if runtime.exchange != ExchangeName.BINANCE_USDM_TESTNET:
        raise TestnetSmokeSafetyError("EXCHANGE must be BINANCE_USDM_TESTNET")
    if not runtime.has_credentials:
        raise TestnetSmokeSafetyError("testnet credentials are required")


def _validate_non_marketable(
    order_config: TestnetSmokeOrderConfig,
    positions: list[ExchangePositionSnapshot],
) -> None:
    if not order_config.require_non_marketable:
        return
    mark_price = _find_mark_price(order_config.symbol, positions)
    if mark_price is None or mark_price <= 0:
        raise TestnetSmokeSafetyError("mark price is required for non-marketable guard")
    margin = order_config.non_marketable_margin
    if not Decimal("0") < margin < Decimal("1"):
        raise TestnetSmokeSafetyError("non_marketable_margin must be between 0 and 1")
    if order_config.side == OrderSide.BUY:
        max_buy_price = mark_price * (Decimal("1") - margin)
        if order_config.limit_price >= max_buy_price:
            raise TestnetSmokeSafetyError(
                f"BUY smoke limit price must be below {max_buy_price} to avoid marketable order"
            )
    if order_config.side == OrderSide.SELL:
        min_sell_price = mark_price * (Decimal("1") + margin)
        if order_config.limit_price <= min_sell_price:
            raise TestnetSmokeSafetyError(
                f"SELL smoke limit price must be above {min_sell_price} to avoid marketable order"
            )


def _find_mark_price(symbol: str, positions: list[ExchangePositionSnapshot]) -> Decimal | None:
    for position in positions:
        if position.symbol == symbol and position.mark_price is not None:
            return position.mark_price
    return None


def _run_reconciliation(
    exchange: ReadWriteSmokeExchange,
    safe_mode: SafeModeController,
) -> tuple[ReconciliationReport, PositionReconciliationReport]:
    order_store = SQLiteOrderStore(":memory:")
    position_store = SQLitePositionStore(":memory:")
    order_reconciler = OrderReconciler(order_store, exchange, safe_mode)
    position_reconciler = PositionReconciler(position_store, exchange, safe_mode)
    position_reconciler.refresh_local_positions_from_exchange()
    return order_reconciler.reconcile_open_orders(), position_reconciler.reconcile_positions()
