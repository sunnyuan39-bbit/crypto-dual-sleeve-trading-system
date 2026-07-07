from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass
class ManualOverrideState:
    pause_all: bool = False
    paused_sleeves: set[str] = field(default_factory=set)
    paused_symbols: set[str] = field(default_factory=set)
    safe_mode_forced: bool = False
    updated_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))
    reason: str | None = None

    def should_block_symbol(self, symbol: str, sleeve_id: str) -> bool:
        return self.pause_all or sleeve_id in self.paused_sleeves or symbol in self.paused_symbols

    def pause_everything(self, reason: str) -> None:
        self.pause_all = True
        self.reason = reason
        self.updated_at = datetime.now(tz=UTC)

    def pause_sleeve(self, sleeve_id: str, reason: str) -> None:
        self.paused_sleeves.add(sleeve_id)
        self.reason = reason
        self.updated_at = datetime.now(tz=UTC)

    def pause_symbol(self, symbol: str, reason: str) -> None:
        self.paused_symbols.add(symbol)
        self.reason = reason
        self.updated_at = datetime.now(tz=UTC)
