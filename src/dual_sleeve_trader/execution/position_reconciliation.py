from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from dual_sleeve_trader.core.account import ExchangePositionSnapshot
from dual_sleeve_trader.execution.safe_mode import SafeModeController


class PositionStore(Protocol):
    def list_positions(self, include_flat: bool = False) -> list[ExchangePositionSnapshot]: ...
    def upsert_position(self, position: ExchangePositionSnapshot) -> None: ...


class PositionExchange(Protocol):
    def fetch_position_snapshots(self, symbol: str | None = None) -> list[ExchangePositionSnapshot]: ...


@dataclass(frozen=True)
class PositionReconciliationReport:
    consistent: bool
    missing_on_exchange: tuple[tuple[str, str], ...]
    unknown_on_local: tuple[tuple[str, str], ...]
    amount_mismatches: tuple[tuple[str, str], ...]
    error: str | None = None


class PositionReconciler:
    def __init__(
        self,
        store: PositionStore,
        exchange: PositionExchange,
        safe_mode: SafeModeController,
        amount_tolerance: Decimal = Decimal("0"),
    ) -> None:
        self.store = store
        self.exchange = exchange
        self.safe_mode = safe_mode
        self.amount_tolerance = amount_tolerance

    def reconcile_positions(self) -> PositionReconciliationReport:
        try:
            local_positions = self.store.list_positions(include_flat=False)
            remote_positions = [
                position
                for position in self.exchange.fetch_position_snapshots()
                if not position.is_flat
            ]
        except Exception as exc:
            reason = f"POSITION_RECONCILIATION_FETCH_FAILED: {exc}"
            self.safe_mode.enter(reason)
            return PositionReconciliationReport(False, (), (), (), reason)

        local_by_key = {position.key: position for position in local_positions}
        remote_by_key = {position.key: position for position in remote_positions}

        missing_on_exchange = tuple(sorted(set(local_by_key) - set(remote_by_key)))
        unknown_on_local = tuple(sorted(set(remote_by_key) - set(local_by_key)))
        amount_mismatches = tuple(
            sorted(
                key
                for key in set(local_by_key) & set(remote_by_key)
                if abs(local_by_key[key].position_amt - remote_by_key[key].position_amt)
                > self.amount_tolerance
            )
        )

        consistent = not missing_on_exchange and not unknown_on_local and not amount_mismatches
        if not consistent:
            self.safe_mode.enter(
                "POSITION_RECONCILIATION_MISMATCH "
                f"missing={missing_on_exchange} unknown={unknown_on_local} amount={amount_mismatches}"
            )

        return PositionReconciliationReport(
            consistent=consistent,
            missing_on_exchange=missing_on_exchange,
            unknown_on_local=unknown_on_local,
            amount_mismatches=amount_mismatches,
        )

    def refresh_local_positions_from_exchange(self) -> list[ExchangePositionSnapshot]:
        positions = self.exchange.fetch_position_snapshots()
        for position in positions:
            self.store.upsert_position(position)
        return positions
