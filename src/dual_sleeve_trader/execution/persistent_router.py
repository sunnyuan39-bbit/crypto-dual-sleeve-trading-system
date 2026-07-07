from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from dual_sleeve_trader.core.models import OrderIntent, OrderRecord
from dual_sleeve_trader.execution.order_router import OrderRouter, RouteResult


class OrderStoreWriter(Protocol):
    def upsert_order(self, order: OrderRecord) -> None: ...


@dataclass
class PersistentOrderRouter:
    router: OrderRouter
    store: OrderStoreWriter

    def route(self, intent: OrderIntent) -> RouteResult:
        result = self.router.route(intent)
        if result.accepted and result.order is not None and result.reason == "SUBMITTED_TO_SIM_OR_TESTNET":
            self.store.upsert_order(result.order)
        return result
