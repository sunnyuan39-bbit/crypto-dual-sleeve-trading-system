from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from dual_sleeve_trader.config.runtime import RuntimeConfig
from dual_sleeve_trader.exchange.factory import build_exchange_adapter


@dataclass(frozen=True)
class SmokeResult:
    ok: bool
    mode: str
    exchange: str
    used_real_testnet: bool
    checks: dict[str, Any]


def run_testnet_smoke(config: RuntimeConfig, require_real_testnet: bool = False) -> SmokeResult:
    adapter = build_exchange_adapter(config, allow_inert_fallback=not require_real_testnet)
    used_real_testnet = config.has_binance_credentials and config.exchange == "BINANCE_USDM_TESTNET"

    filters = adapter.get_symbol_filters(config.smoke_symbol)
    checks: dict[str, Any] = {
        "symbol": filters.symbol,
        "tick_size": str(filters.tick_size),
        "step_size": str(filters.step_size),
        "min_notional": str(filters.min_notional),
    }

    if hasattr(adapter, "fetch_account_snapshot"):
        account = adapter.fetch_account_snapshot()  # type: ignore[attr-defined]
        checks["account_total_wallet_balance"] = str(account.total_wallet_balance)

    if hasattr(adapter, "fetch_position_snapshots"):
        positions = adapter.fetch_position_snapshots(config.smoke_symbol)  # type: ignore[attr-defined]
        checks["positions_count"] = len(positions)

    return SmokeResult(
        ok=True,
        mode=config.trading_mode.value,
        exchange=config.exchange.value,
        used_real_testnet=used_real_testnet,
        checks=checks,
    )
