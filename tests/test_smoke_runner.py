from dual_sleeve_trader.config.runtime import ExchangeName, RuntimeConfig
from dual_sleeve_trader.core.enums import TradingMode
from dual_sleeve_trader.ops.smoke import run_testnet_smoke


def test_smoke_runner_works_in_inert_mode() -> None:
    config = RuntimeConfig(
        trading_mode=TradingMode.SIGNAL_ONLY,
        exchange=ExchangeName.INERT_TESTNET,
        smoke_symbol="BTCUSDT",
    )

    result = run_testnet_smoke(config)

    assert result.ok
    assert not result.used_real_testnet
    assert result.checks["symbol"] == "BTCUSDT"
