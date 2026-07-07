from dual_sleeve_trader.config.runtime import ExchangeName, load_runtime_config
from dual_sleeve_trader.core.enums import TradingMode


def test_load_runtime_config_defaults_to_inert(monkeypatch) -> None:
    monkeypatch.delenv("TRADING_MODE", raising=False)
    monkeypatch.delenv("EXCHANGE", raising=False)
    monkeypatch.delenv("BINANCE_API_KEY", raising=False)
    monkeypatch.delenv("BINANCE_API_SECRET", raising=False)

    config = load_runtime_config(env_file=None)

    assert config.trading_mode == TradingMode.SIGNAL_ONLY
    assert config.exchange == ExchangeName.INERT_TESTNET
    assert not config.has_binance_credentials


def test_load_runtime_config_reads_env(monkeypatch) -> None:
    monkeypatch.setenv("TRADING_MODE", "EXCHANGE_TESTNET")
    monkeypatch.setenv("EXCHANGE", "BINANCE_USDM_TESTNET")
    monkeypatch.setenv("BINANCE_API_KEY", "key")
    monkeypatch.setenv("BINANCE_API_SECRET", "secret")
    monkeypatch.setenv("SMOKE_SYMBOL", "ETHUSDT")

    config = load_runtime_config(env_file=None)

    assert config.trading_mode == TradingMode.EXCHANGE_TESTNET
    assert config.exchange == ExchangeName.BINANCE_USDM_TESTNET
    assert config.has_binance_credentials
    assert config.smoke_symbol == "ETHUSDT"
