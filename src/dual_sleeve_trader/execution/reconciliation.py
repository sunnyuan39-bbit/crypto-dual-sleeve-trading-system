from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from dual_sleeve_trader.core.enums import OrderStatus
from dual_sleeve_trader.core.models import OrderRecord
from dual_sleeve_trader.exchange.interfaces import ExchangeAdapter
from dual_sleeve_trader.execution.safe_mode import SafeModeController


class LocalOrderStore(Protocol):
    def list_open_orders(self) -> list[OrderRecord]: ...


@dataclass(frozen=True)
class ReconciliationReport:
    consistent: bool
    missing_on_exchange: tuple[str, ...]
    unknown_on_local: tuple[str, ...]
    status_mismatches: tuple[str, ...]
    error: str | None = None


class OrderReconciler:
    def __init__(
        self,
        store: LocalOrderStore,
        exchange: ExchangeAdapter,
        safe_mode: SafeModeController,
    ) -> None:
        self.store = store
        self.exchange = exchange
        self.safe_mode = safe_mode

    def reconcile_open_orders(self) -> ReconciliationReport:
        try:
            local_orders = self.store.list_open_orders()
            exchange_orders = self.exchange.fetch_open_orders()
        except Exception as exc:
            reason = f"RECONCILIATION_FETCH_FAILED: {exc}"
            self.safe_mode.enter(reason)
            return ReconciliationReport(
                consistent=False,
                missing_on_exchange=(),
                unknown_on_local=(),
                status_mismatches=(),
                error=reason,
            )

        local_by_id = {order.client_order_id: order for order in local_orders}
        exchange_by_id = {order.client_order_id: order for order in exchange_orders}

        missing_on_exchange = tuple(sorted(set(local_by_id) - set(exchange_by_id)))
        unknown_on_local = tuple(sorted(set(exchange_by_id) - set(local_by_id)))
        status_mismatches = tuple(
            sorted(
                client_id
                for client_id in set(local_by_id) & set(exchange_by_id)
                if _is_meaningful_status_mismatch(
                    local_by_id[client_id].status,
                    exchange_by_id[client_id].status,
                )
            )
        )

        consistent = not missing_on_exchange and not unknown_on_local and not status_mismatches
        if not consistent:
            self.safe_mode.enter(
                "RECONCILIATION_MISMATCH "
                f"missing={missing_on_exchange} unknown={unknown_on_local} "
                f"status={status_mismatches}"
            )

        return ReconciliationReport(
            consistent=consistent,
            missing_on_exchange=missing_on_exchange,
            unknown_on_local=unknown_on_local,
            status_mismatches=status_mismatches,
        )


def _is_meaningful_status_mismatch(local: OrderStatus, exchange: OrderStatus) -> bool:
    if OrderStatus.UNKNOWN in {local, exchange}:
        return False
    if local == exchange:
        return False
    terminal = {OrderStatus.FILLED, OrderStatus.CANCELED, OrderStatus.REJECTED, OrderStatus.EXPIRED}
    return local in terminal or exchange in terminal
