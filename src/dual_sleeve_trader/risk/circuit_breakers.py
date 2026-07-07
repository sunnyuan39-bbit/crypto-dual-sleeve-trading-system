from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from dual_sleeve_trader.core.enums import CircuitAction, SleeveId
from dual_sleeve_trader.core.models import AccountSnapshot


@dataclass(frozen=True)
class CircuitBreakerConfig:
    global_daily_loss_stop: Decimal = Decimal("-3000")
    sleeve_a_daily_loss_stop: Decimal = Decimal("-1000")
    sleeve_a_monthly_loss_stop: Decimal = Decimal("-8000")
    sleeve_b_weekly_loss_stop: Decimal = Decimal("-3200")


@dataclass(frozen=True)
class CircuitDecision:
    global_actions: tuple[CircuitAction, ...] = ()
    sleeve_actions: dict[SleeveId, tuple[CircuitAction, ...]] = field(default_factory=dict)
    reasons: tuple[str, ...] = ()

    @property
    def global_stop(self) -> bool:
        return bool(self.global_actions)

    def stopped(self, sleeve_id: SleeveId) -> bool:
        return sleeve_id in self.sleeve_actions


class CircuitBreakerEngine:
    def __init__(self, config: CircuitBreakerConfig | None = None) -> None:
        self.config = config or CircuitBreakerConfig()

    def evaluate(self, account: AccountSnapshot) -> CircuitDecision:
        global_actions: list[CircuitAction] = []
        sleeve_actions: dict[SleeveId, list[CircuitAction]] = {}
        reasons: list[str] = []

        if account.daily_pnl <= self.config.global_daily_loss_stop:
            global_actions.extend([
                CircuitAction.CANCEL_ENTRIES,
                CircuitAction.FLATTEN_A_REDUCE_ONLY,
                CircuitAction.BLOCK_NEW_ENTRIES,
            ])
            reasons.append("GLOBAL_DAILY_LOSS_STOP")

        sleeve_a = account.sleeves.get(SleeveId.A)
        if sleeve_a is not None:
            if sleeve_a.daily_pnl <= self.config.sleeve_a_daily_loss_stop:
                sleeve_actions.setdefault(SleeveId.A, []).extend([
                    CircuitAction.BLOCK_NEW_ENTRIES,
                    CircuitAction.EXIT_ONLY,
                ])
                reasons.append("SLEEVE_A_DAILY_LOSS_STOP")
            if sleeve_a.monthly_pnl <= self.config.sleeve_a_monthly_loss_stop:
                sleeve_actions.setdefault(SleeveId.A, []).extend([
                    CircuitAction.BLOCK_NEW_ENTRIES,
                    CircuitAction.EXIT_ONLY,
                ])
                reasons.append("SLEEVE_A_MONTHLY_LOSS_STOP")

        sleeve_b = account.sleeves.get(SleeveId.B)
        if sleeve_b is not None and sleeve_b.weekly_pnl <= self.config.sleeve_b_weekly_loss_stop:
            sleeve_actions.setdefault(SleeveId.B, []).extend([
                CircuitAction.BLOCK_NEW_ENTRIES,
                CircuitAction.EXIT_ONLY,
            ])
            reasons.append("SLEEVE_B_WEEKLY_LOSS_STOP")

        return CircuitDecision(
            global_actions=tuple(global_actions),
            sleeve_actions={k: tuple(v) for k, v in sleeve_actions.items()},
            reasons=tuple(reasons),
        )
