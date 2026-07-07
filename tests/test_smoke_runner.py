import pytest

from dual_sleeve_trader.config.runtime import ExchangeName, RuntimeConfig
from dual_sleeve_trader.core.enums import TradingMode
from dual_sleeve_trader.exchange.factory import MissingTestnetCredentials
from dual_sleeve_trader.ops.smoke import run_testnet_smoke


def test_smoke_runner_works_without_keys_in_inert_mode() -> None:
    config = RuntimeConfig(
        trading_mode=TradingMode.SIGNAL_ONLY,
        exchange=ExchangeName.INERT_TESTNET,
        smoke_symbol="BTCUSDT",
    )

    result = run_testnet_smoke(config)

    assert result.ok
    assert not result.used_real_testnet
    assert result.checks["symbol"] == "BTCUSDT"


def test_smoke_runner_can_require_real_testnet_credentials() -> None:
    config = RuntimeConfig(
        trading_mode=TradingMode.EXCHANGE_TESTNET,
        exchange=ExchangeName.BINANCE_USDM_TESTNET,
        smoke_symbol="BTCUSDT",
    )

    with pytest.raises(MissingTestnetCredentials):
        run_testnet_smoke(config, require_real_testnet=True)
