from decimal import Decimal

from dual_sleeve_trader.core.enums import CircuitAction, SleeveId
from dual_sleeve_trader.core.models import AccountSnapshot, SleeveLedgerSnapshot
from dual_sleeve_trader.risk.circuit_breakers import CircuitBreakerEngine


def test_global_daily_loss_blocks_entries() -> None:
    account = AccountSnapshot(
        starting_equity=Decimal("120000"),
        daily_pnl=Decimal("-3001"),
        sleeves={
            SleeveId.A: SleeveLedgerSnapshot(SleeveId.A, Decimal("40000")),
            SleeveId.B: SleeveLedgerSnapshot(SleeveId.B, Decimal("80000")),
        },
    )
    decision = CircuitBreakerEngine().evaluate(account)
    assert decision.global_stop
    assert CircuitAction.BLOCK_NEW_ENTRIES in decision.global_actions


def test_sleeve_a_daily_loss_enters_exit_only() -> None:
    account = AccountSnapshot(
        starting_equity=Decimal("120000"),
        daily_pnl=Decimal("-1000"),
        sleeves={
            SleeveId.A: SleeveLedgerSnapshot(SleeveId.A, Decimal("40000"), daily_pnl=Decimal("-1000")),
            SleeveId.B: SleeveLedgerSnapshot(SleeveId.B, Decimal("80000")),
        },
    )
    decision = CircuitBreakerEngine().evaluate(account)
    assert decision.stopped(SleeveId.A)
    assert CircuitAction.EXIT_ONLY in decision.sleeve_actions[SleeveId.A]
