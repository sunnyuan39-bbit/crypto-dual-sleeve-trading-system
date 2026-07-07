from decimal import Decimal

from dual_sleeve_trader.config.runtime import ExchangeName, RuntimeConfig
from dual_sleeve_trader.core.account import ExchangePositionSnapshot
from dual_sleeve_trader.core.enums import TradingMode
from dual_sleeve_trader.execution.position_reconciliation import PositionReconciler
from dual_sleeve_trader.execution.reconciliation import OrderReconciler
from dual_sleeve_trader.execution.safe_mode import SafeModeController
from dual_sleeve_trader.ops.daemon import DaemonConfig, DaemonRunner, build_daemon_runner, daemon_result_to_dict
from dual_sleeve_trader.storage.position_store import SQLitePositionStore
from dual_sleeve_trader.storage.sqlite_store import SQLiteOrderStore


class MemoryAlerts:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def send(self, message: str) -> None:
        self.messages.append(message)


class EmptyExchange:
    def fetch_open_orders(self):
        return []

    def fetch_position_snapshots(self, symbol: str | None = None):
        return []


class OnePositionExchange(EmptyExchange):
    def fetch_position_snapshots(self, symbol: str | None = None):
        return [ExchangePositionSnapshot("BTCUSDT", "BOTH", Decimal("0.5"))]


def test_daemon_runner_once_consistent(tmp_path) -> None:
    safe_mode = SafeModeController()
    alerts = MemoryAlerts()
    order_store = SQLiteOrderStore(tmp_path / "state.sqlite3")
    position_store = SQLitePositionStore(tmp_path / "state.sqlite3")
    exchange = EmptyExchange()
    runner = DaemonRunner(
        OrderReconciler(order_store, exchange, safe_mode),
        PositionReconciler(position_store, exchange, safe_mode),
        safe_mode,
        alerts,
        DaemonConfig(max_iterations=1),
    )

    results = runner.run()

    assert len(results) == 1
    assert results[0].consistent
    assert alerts.messages == []


def test_daemon_runner_alerts_on_position_mismatch(tmp_path) -> None:
    safe_mode = SafeModeController()
    alerts = MemoryAlerts()
    order_store = SQLiteOrderStore(tmp_path / "state.sqlite3")
    position_store = SQLitePositionStore(tmp_path / "state.sqlite3")
    runner = DaemonRunner(
        OrderReconciler(order_store, OnePositionExchange(), safe_mode),
        PositionReconciler(position_store, OnePositionExchange(), safe_mode),
        safe_mode,
        alerts,
        DaemonConfig(max_iterations=5, interval_seconds=0, stop_on_mismatch=True),
    )

    results = runner.run()

    assert len(results) == 1
    assert not results[0].consistent
    assert results[0].safe_mode_active
    assert alerts.messages


def test_build_daemon_runner_uses_runtime_state_path(tmp_path) -> None:
    config = RuntimeConfig(
        trading_mode=TradingMode.SIGNAL_ONLY,
        exchange=ExchangeName.INERT_TESTNET,
        state_db_path=str(tmp_path / "daemon.sqlite3"),
    )

    runner = build_daemon_runner(config, DaemonConfig(max_iterations=1))
    results = runner.run()

    assert results[0].consistent
    assert (tmp_path / "daemon.sqlite3").exists()


def test_daemon_result_to_dict() -> None:
    config = RuntimeConfig(TradingMode.SIGNAL_ONLY, ExchangeName.INERT_TESTNET)
    runner = build_daemon_runner(config, DaemonConfig(max_iterations=1))
    result = runner.run()[0]

    payload = daemon_result_to_dict(result)

    assert payload["consistent"] is True
    assert payload["safe_mode_active"] is False
