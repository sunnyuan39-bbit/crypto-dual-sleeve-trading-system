import pytest

from dual_sleeve_trader.config.runtime import ExchangeName, RuntimeConfig
from dual_sleeve_trader.core.enums import TradingMode
from dual_sleeve_trader.exchange.binance_rest import BinanceFuturesTestnetRestAdapter
from dual_sleeve_trader.exchange.binance_testnet import BinanceUsdmTestnetAdapter
from dual_sleeve_trader.exchange.factory import MissingTestnetCredentials, build_exchange_adapter


def test_exchange_factory_uses_inert_without_keys() -> None:
    config = RuntimeConfig(
        trading_mode=TradingMode.SIGNAL_ONLY,
        exchange=ExchangeName.BINANCE_USDM_TESTNET,
    )

    adapter = build_exchange_adapter(config, allow_inert_fallback=True)

    assert isinstance(adapter, BinanceUsdmTestnetAdapter)


def test_exchange_factory_requires_keys_when_fallback_disabled() -> None:
    config = RuntimeConfig(
        trading_mode=TradingMode.EXCHANGE_TESTNET,
        exchange=ExchangeName.BINANCE_USDM_TESTNET,
    )

    with pytest.raises(MissingTestnetCredentials):
        build_exchange_adapter(config, allow_inert_fallback=False)


def test_exchange_factory_builds_real_testnet_adapter_with_keys() -> None:
    config = RuntimeConfig(
        trading_mode=TradingMode.EXCHANGE_TESTNET,
        exchange=ExchangeName.BINANCE_USDM_TESTNET,
        binance_api_key="key",
        binance_api_secret="secret",
    )

    adapter = build_exchange_adapter(config, allow_inert_fallback=False)

    assert isinstance(adapter, BinanceFuturesTestnetRestAdapter)
