from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class AlertSink(Protocol):
    def send(self, message: str) -> None:
        ...


@dataclass
class ConsoleAlertSink:
    prefix: str = "[dual-sleeve]"

    def send(self, message: str) -> None:
        print(f"{self.prefix} {message}")
