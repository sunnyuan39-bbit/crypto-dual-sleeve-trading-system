from __future__ import annotations

from dual_sleeve_trader.core.enums import TradingMode
from dual_sleeve_trader.execution.safe_mode import SafeModeController
from dual_sleeve_trader.ops.alerts import ConsoleAlertSink


def main() -> None:
    mode = TradingMode.SIGNAL_ONLY
    safe_mode = SafeModeController()
    alerts = ConsoleAlertSink()
    alerts.send(f"Starting production skeleton in {mode.value}; safe_mode={safe_mode.state.value}")


if __name__ == "__main__":
    main()
