from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from dual_sleeve_trader.core.enums import OrderStatus
from dual_sleeve_trader.core.exchange_order import ExchangeOrderSnapshot
from dual_sleeve_trader.core.models import OrderRecord
from dual_sleeve_trader.execution.safe_mode import SafeModeController


class RepairAction(StrEnum):
    NONE = "NONE"
    UPDATED_LOCAL_FROM_EXCHANGE = "UPDATED_LOCAL_FROM_EXCHANGE"
    ENTERED_SAFE_MODE = "ENTERED_SAFE_MODE"
    MANUAL_REVIEW = "MANUAL_REVIEW"


class RepairReason(StrEnum):
    CONSISTENT = "CONSISTENT"
    LOCAL_ORDER_MISSING = "LOCAL_ORDER_MISSING"
    EXCHANGE_ORDER_MISSING = "EXCHANGE_ORDER_MISSING"
    EXCHANGE_FETCH_FAILED = "EXCHANGE_FETCH_FAILED"
    LOCAL_UPDATED = "LOCAL_UPDATED"
    SYMBOL_MISMATCH = "SYMBOL_MISMATCH"


class RepairOrderStore(Protocol):
    def get_order(self, client_order_id: str) -> OrderRecord | None: ...
    def upsert_order(self, order: OrderRecord) -> None: ...


class OrderQueryAdapter(Protocol):
    def query_order(self, symbol: str, client_order_id: str) -> ExchangeOrderSnapshot | None: ...


@dataclass(frozen=True)
class RepairRecommendation:
    client_order_id: str
    action: RepairAction
    reason: RepairReason
    message: str


class OrderRepairEngine:
    def __init__(
        self,
        store: RepairOrderStore,
        exchange: OrderQueryAdapter,
        safe_mode: SafeModeController,
    ) -> None:
        self.store = store
        self.exchange = exchange
        self.safe_mode = safe_mode

    def repair_by_client_order_id(self, client_order_id: str) -> RepairRecommendation:
        local = self.store.get_order(client_order_id)
        if local is None:
            self.safe_mode.enter(f"REPAIR_LOCAL_ORDER_MISSING {client_order_id}")
            return RepairRecommendation(
                client_order_id,
                RepairAction.MANUAL_REVIEW,
                RepairReason.LOCAL_ORDER_MISSING,
                "Local order is missing; cannot infer sleeve ownership from exchange alone.",
            )

        try:
            remote = self.exchange.query_order(local.intent.symbol, client_order_id)
        except Exception as exc:
            self.safe_mode.enter(f"REPAIR_QUERY_FAILED {client_order_id}: {exc}")
            return RepairRecommendation(
                client_order_id,
                RepairAction.ENTERED_SAFE_MODE,
                RepairReason.EXCHANGE_FETCH_FAILED,
                str(exc),
            )

        if remote is None:
            self.safe_mode.enter(f"REPAIR_EXCHANGE_ORDER_MISSING {client_order_id}")
            return RepairRecommendation(
                client_order_id,
                RepairAction.MANUAL_REVIEW,
                RepairReason.EXCHANGE_ORDER_MISSING,
                "Exchange did not return the local order; manual review required.",
            )

        if remote.symbol != local.intent.symbol:
            self.safe_mode.enter(f"REPAIR_SYMBOL_MISMATCH {client_order_id}")
            return RepairRecommendation(
                client_order_id,
                RepairAction.MANUAL_REVIEW,
                RepairReason.SYMBOL_MISMATCH,
                f"Local symbol {local.intent.symbol} != exchange symbol {remote.symbol}.",
            )

        changed = _apply_remote_snapshot(local, remote)
        if changed:
            self.store.upsert_order(local)
            return RepairRecommendation(
                client_order_id,
                RepairAction.UPDATED_LOCAL_FROM_EXCHANGE,
                RepairReason.LOCAL_UPDATED,
                "Local order status/fill fields updated from exchange snapshot.",
            )

        return RepairRecommendation(
            client_order_id,
            RepairAction.NONE,
            RepairReason.CONSISTENT,
            "Local order already matches exchange snapshot.",
        )


def _apply_remote_snapshot(local: OrderRecord, remote: ExchangeOrderSnapshot) -> bool:
    changed = False
    if local.status != remote.status:
        local.status = remote.status
        changed = True
    if local.exchange_order_id != remote.exchange_order_id:
        local.exchange_order_id = remote.exchange_order_id
        changed = True
    if local.filled_quantity != remote.executed_quantity:
        local.filled_quantity = remote.executed_quantity
        changed = True
    if local.average_fill_price != remote.average_price:
        local.average_fill_price = remote.average_price
        changed = True
    return changed


TERMINAL_STATUSES = {
    OrderStatus.FILLED,
    OrderStatus.CANCELED,
    OrderStatus.REJECTED,
    OrderStatus.EXPIRED,
}
