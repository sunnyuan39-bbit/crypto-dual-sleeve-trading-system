from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from dual_sleeve_trader.core.enums import SafeModeState


@dataclass
class SafeModeController:
    state: SafeModeState = SafeModeState.NORMAL
    reasons: list[str] = field(default_factory=list)
    updated_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))

    def enter(self, reason: str) -> None:
        self.state = SafeModeState.SAFE_MODE
        self.reasons.append(reason)
        self.updated_at = datetime.now(tz=UTC)

    def exit(self, reason: str) -> None:
        self.state = SafeModeState.NORMAL
        self.reasons.append(f"EXIT: {reason}")
        self.updated_at = datetime.now(tz=UTC)

    @property
    def allows_new_entries(self) -> bool:
        return self.state == SafeModeState.NORMAL
