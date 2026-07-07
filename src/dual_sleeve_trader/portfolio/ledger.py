from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from dual_sleeve_trader.core.enums import SleeveId
from dual_sleeve_trader.core.models import AccountSnapshot, SleeveLedgerSnapshot


@dataclass
class VirtualSleeveLedger:
    account_starting_equity: Decimal = Decimal("120000")
    sleeves: dict[SleeveId, SleeveLedgerSnapshot] = field(
        default_factory=lambda: {
            SleeveId.A: SleeveLedgerSnapshot(SleeveId.A, Decimal("40000")),
            SleeveId.B: SleeveLedgerSnapshot(SleeveId.B, Decimal("80000")),
        }
    )

    def snapshot(self) -> AccountSnapshot:
        daily_pnl = sum((s.daily_pnl for s in self.sleeves.values()), Decimal("0"))
        return AccountSnapshot(
            starting_equity=self.account_starting_equity,
            daily_pnl=daily_pnl,
            sleeves=dict(self.sleeves),
        )

    def update_sleeve(self, snapshot: SleeveLedgerSnapshot) -> None:
        self.sleeves[snapshot.sleeve_id] = snapshot
