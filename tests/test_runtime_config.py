from dual_sleeve_trader.config.runtime import ExchangeName, RuntimeConfig
from dual_sleeve_trader.core.enums import TradingMode


def test_runtime_config_credentials_flag() -> None:
    config = RuntimeConfig(
        trading_mode=TradingMode.EXCHANGE_TESTNET,
        exchange=ExchangeName.BINANCE_USDM_TESTNET,
        api_key="key",
        api_secret="secret",
    )

    assert config.has_credentials


def test_runtime_config_no_credentials_flag() -> None:
    config = RuntimeConfig(
        trading_mode=TradingMode.SIGNAL_ONLY,
        exchange=ExchangeName.INERT_TESTNET,
    )

    assert not config.has_credentials
