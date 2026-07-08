from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from dual_sleeve_trader.core.account import AccountSnapshotV3, ExchangePositionSnapshot
from dual_sleeve_trader.core.enums import OrderAction, OrderSide, OrderType, PositionSide, SleeveId, TradingMode
from dual_sleeve_trader.core.models import OrderIntent, SymbolFilters
from dual_sleeve_trader.execution.order_router import OrderRouter, RouteResult
from dual_sleeve_trader.execution.persistent_router import PersistentOrderRouter
from dual_sleeve_trader.execution.safe_mode import SafeModeController
from dual_sleeve_trader.execution.sleeve_b_allocator import (
    SleeveBAllocationDecision,
    SleeveBExecutionAllocator,
    SleeveBSignalCandidate,
)
from dual_sleeve_trader.storage.sqlite_store import SQLiteOrderStore


class SleeveBLoopExchange(Protocol):
    def fetch_account_snapshot(self) -> AccountSnapshotV3: ...
    def fetch_position_snapshots(self, symbol: str | None = None) -> list[ExchangePositionSnapshot]: ...
    def get_symbol_filters(self, symbol: str) -> SymbolFilters: ...


@dataclass(frozen=True)
class SleeveBAutoLoopConfig:
    max_new_orders_per_run: int = 1
    require_ack: bool = False
    limit_price_offset_bps: Decimal = Decimal("5")


@dataclass(frozen=True)
class SleeveBAutoLoopDecision:
    symbol: str
    accepted: bool
    allocation: SleeveBAllocationDecision
    route_result: RouteResult | None
    reason: str


@dataclass(frozen=True)
class SleeveBAutoLoopRunResult:
    decisions: tuple[SleeveBAutoLoopDecision, ...]
    submitted_orders: int
    safe_mode_active: bool


class SleeveBAutoTestnetLoop:
    def __init__(
        self,
        exchange: SleeveBLoopExchange,
        order_store: SQLiteOrderStore,
        safe_mode: SafeModeController,
        allocator: SleeveBExecutionAllocator | None = None,
        config: SleeveBAutoLoopConfig | None = None,
    ) -> None:
        self.exchange = exchange
        self.order_store = order_store
        self.safe_mode = safe_mode
        self.allocator = allocator or SleeveBExecutionAllocator()
        self.config = config or SleeveBAutoLoopConfig()

    def run_once(self, candidates: list[SleeveBSignalCandidate]) -> SleeveBAutoLoopRunResult:
        if not self.config.require_ack:
            return SleeveBAutoLoopRunResult(
                decisions=tuple(
                    SleeveBAutoLoopDecision(
                        symbol=candidate.symbol,
                        accepted=False,
                        allocation=self.allocator._reject(candidate, "ACK_REQUIRED"),
                        route_result=None,
                        reason="ACK_REQUIRED",
                    )
                    for candidate in candidates
                ),
                submitted_orders=0,
                safe_mode_active=not self.safe_mode.allows_new_entries,
            )

        account = self.exchange.fetch_account_snapshot()
        all_positions = self.exchange.fetch_position_snapshots()
        router = PersistentOrderRouter(
            OrderRouter(TradingMode.EXCHANGE_TESTNET, self.exchange, self.safe_mode),
            self.order_store,
        )
        decisions: list[SleeveBAutoLoopDecision] = []
        submitted = 0

        for candidate in candidates:
            if submitted >= self.config.max_new_orders_per_run:
                decisions.append(self._skip(candidate, "MAX_NEW_ORDERS_PER_RUN_REACHED"))
                continue
            if not self.safe_mode.allows_new_entries:
                decisions.append(self._skip(candidate, "SAFE_MODE_BLOCKS_NEW_ENTRIES"))
                continue

            filters = self.exchange.get_symbol_filters(candidate.symbol)
            allocation = self.allocator.allocate(candidate, account, all_positions, filters)
            if not allocation.accepted:
                decisions.append(
                    SleeveBAutoLoopDecision(candidate.symbol, False, allocation, None, allocation.reason)
                )
                continue

            intent = self._allocation_to_intent(candidate, allocation)
            route_result = router.route(intent)
            if route_result.accepted:
                submitted += 1
            decisions.append(
                SleeveBAutoLoopDecision(
                    symbol=candidate.symbol,
                    accepted=route_result.accepted,
                    allocation=allocation,
                    route_result=route_result,
                    reason=route_result.reason,
                )
            )

        return SleeveBAutoLoopRunResult(
            decisions=tuple(decisions),
            submitted_orders=submitted,
            safe_mode_active=not self.safe_mode.allows_new_entries,
        )

    def _allocation_to_intent(
        self,
        candidate: SleeveBSignalCandidate,
        allocation: SleeveBAllocationDecision,
    ) -> OrderIntent:
        side = OrderSide.BUY if candidate.side == PositionSide.LONG else OrderSide.SELL
        return OrderIntent(
            sleeve_id=SleeveId.B,
            symbol=candidate.symbol,
            side=side,
            order_type=OrderType.LIMIT,
            action=OrderAction.ENTRY,
            quantity=allocation.quantity,
            price=_entry_limit_price(candidate, self.config.limit_price_offset_bps),
            reduce_only=False,
            setup_id=candidate.setup_id,
            metadata={
                "source": "sleeve_b_auto_testnet_loop",
                "allocator_reason": allocation.reason,
                "initial_margin": str(allocation.initial_margin),
                "risk_amount": str(allocation.risk_amount),
                "leverage": str(allocation.leverage),
            },
        )

    def _skip(self, candidate: SleeveBSignalCandidate, reason: str) -> SleeveBAutoLoopDecision:
        return SleeveBAutoLoopDecision(
            symbol=candidate.symbol,
            accepted=False,
            allocation=self.allocator._reject(candidate, reason),
            route_result=None,
            reason=reason,
        )


def _entry_limit_price(candidate: SleeveBSignalCandidate, offset_bps: Decimal) -> Decimal:
    offset = offset_bps / Decimal("10000")
    if candidate.side == PositionSide.LONG:
        return candidate.entry_price * (Decimal("1") - offset)
    return candidate.entry_price * (Decimal("1") + offset)
