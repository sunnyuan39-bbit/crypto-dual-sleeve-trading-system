from __future__ import annotations

import os
from dataclasses import dataclass
from enum import StrEnum

from dotenv import load_dotenv

from dual_sleeve_trader.core.enums import TradingMode


class ExchangeName(StrEnum):
    BINANCE_USDM_TESTNET = "BINANCE_USDM_TESTNET"
    INERT_TESTNET = "INERT_TESTNET"


@dataclass(frozen=True)
class RuntimeConfig:
    trading_mode: TradingMode
    exchange: ExchangeName
    api_key: str | None = None
    api_secret: str | None = None
    smoke_symbol: str = "BTCUSDT"
    state_db_path: str = "local_state.sqlite3"

    @property
    def has_credentials(self) -> bool:
        return bool(self.api_key and self.api_secret)


def load_runtime_config(env_file: str | None = None) -> RuntimeConfig:
    load_dotenv(env_file, override=False) if env_file else load_dotenv(override=False)
    return RuntimeConfig(
        trading_mode=TradingMode(os.getenv("TRADING_MODE", "SIGNAL_ONLY")),
        exchange=ExchangeName(os.getenv("EXCHANGE", "INERT_TESTNET")),
        api_key=os.getenv("BINANCE_API_KEY") or None,
        api_secret=os.getenv("BINANCE_API_SECRET") or None,
        smoke_symbol=os.getenv("SMOKE_SYMBOL", "BTCUSDT"),
        state_db_path=os.getenv("STATE_DB_PATH", "local_state.sqlite3"),
    )
