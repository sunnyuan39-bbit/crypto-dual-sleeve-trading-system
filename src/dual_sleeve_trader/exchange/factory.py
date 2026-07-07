from __future__ import annotations

from dual_sleeve_trader.config.runtime import ExchangeName, RuntimeConfig
from dual_sleeve_trader.exchange.binance_rest import BinanceCredentials, BinanceFuturesTestnetRestAdapter
from dual_sleeve_trader.exchange.binance_testnet import BinanceUsdmTestnetAdapter
from dual_sleeve_trader.exchange.interfaces import ExchangeAdapter


class MissingTestnetCredentials(RuntimeError):
    pass


def build_exchange_adapter(config: RuntimeConfig, allow_inert_fallback: bool = True) -> ExchangeAdapter:
    if config.exchange == ExchangeName.INERT_TESTNET:
        return BinanceUsdmTestnetAdapter()

    if config.exchange == ExchangeName.BINANCE_USDM_TESTNET:
        if config.has_binance_credentials:
            return BinanceFuturesTestnetRestAdapter(
                BinanceCredentials(
                    api_key=config.binance_api_key or "",
                    api_secret=config.binance_api_secret or "",
                )
            )
        if allow_inert_fallback:
            return BinanceUsdmTestnetAdapter()
        raise MissingTestnetCredentials(
            "BINANCE_API_KEY and BINANCE_API_SECRET are required for real testnet calls"
        )

    raise ValueError(f"Unsupported exchange: {config.exchange}")
