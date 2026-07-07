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
    binance_api_key: str | None = None
    binance_api_secret: str | None = None
    smoke_symbol: str = "BTCUSDT"
    state_db_path: str = "local_state.sqlite3"

    @property
    def has_binance_credentials(self) -> bool:
        return bool(self.binance_api_key and self.binance_api_secret)


def load_runtime_config(env_file: str | None = None) -> RuntimeConfig:
    if env_file is not None:
        load_dotenv(env_file, override=False)
    else:
        load_dotenv(override=False)

    trading_mode_raw = os.getenv("TRADING_MODE", TradingMode.SIGNAL_ONLY.value)
    exchange_raw = os.getenv("EXCHANGE", ExchangeName.INERT_TESTNET.value)

    return RuntimeConfig(
        trading_mode=TradingMode(trading_mode_raw),
        exchange=ExchangeName(exchange_raw),
        binance_api_key=os.getenv("BINANCE_API_KEY") or None,
        binance_api_secret=os.getenv("BINANCE_API_SECRET") or None,
        smoke_symbol=os.getenv("SMOKE_SYMBOL", "BTCUSDT"),
        state_db_path=os.getenv("STATE_DB_PATH", "local_state.sqlite3"),
    )
