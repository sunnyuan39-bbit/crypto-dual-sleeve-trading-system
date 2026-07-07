from __future__ import annotations

from dataclasses import dataclass

from dual_sleeve_trader.core.enums import OrderAction, OrderStatus, TradingMode
from dual_sleeve_trader.core.models import OrderIntent, OrderRecord
from dual_sleeve_trader.exchange.filters import normalize_order_intent
from dual_sleeve_trader.exchange.interfaces import ExchangeAdapter
from dual_sleeve_trader.execution.order_ids import make_client_order_id
from dual_sleeve_trader.execution.order_state_machine import OrderStateMachine
from dual_sleeve_trader.execution.safe_mode import SafeModeController


class LiveTradingDisabled(RuntimeError):
    pass


@dataclass(frozen=True)
class RouteResult:
    accepted: bool
    order: OrderRecord | None
    reason: str


class OrderRouter:
    def __init__(
        self,
        mode: TradingMode,
        exchange: ExchangeAdapter,
        safe_mode: SafeModeController,
        state_machine: OrderStateMachine | None = None,
    ) -> None:
        self.mode = mode
        self.exchange = exchange
        self.safe_mode = safe_mode
        self.state_machine = state_machine or OrderStateMachine()

    def route(self, intent: OrderIntent) -> RouteResult:
        if not self.safe_mode.allows_new_entries and intent.action == OrderAction.ENTRY:
            return RouteResult(False, None, "SAFE_MODE_BLOCKS_NEW_ENTRIES")

        if intent.action != OrderAction.ENTRY and not intent.reduce_only:
            return RouteResult(False, None, "CLOSE_ORDER_MUST_BE_REDUCE_ONLY")

        filters = self.exchange.get_symbol_filters(intent.symbol)
        normalized = normalize_order_intent(intent, filters)
        client_order_id = make_client_order_id(
            normalized.sleeve_id,
            normalized.setup_id or "manual000000",
            normalized.action,
        )
        order = OrderRecord(client_order_id=client_order_id, intent=normalized)

        if self.mode == TradingMode.SIGNAL_ONLY:
            return RouteResult(True, order, "SIGNAL_ONLY_NO_SUBMIT")
        if self.mode in {TradingMode.PAPER_LOCAL, TradingMode.EXCHANGE_TESTNET}:
            self.state_machine.transition(order, OrderStatus.SUBMITTED)
            submitted = self.exchange.submit_order(order)
            return RouteResult(True, submitted, "SUBMITTED_TO_SIM_OR_TESTNET")

        raise LiveTradingDisabled(f"Unsupported mode is disabled: {self.mode}")
