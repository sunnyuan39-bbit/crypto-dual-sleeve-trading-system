from decimal import Decimal

import pytest

from dual_sleeve_trader.config.runtime import ExchangeName, RuntimeConfig
from dual_sleeve_trader.core.account import AccountSnapshotV3, ExchangePositionSnapshot
from dual_sleeve_trader.core.enums import OrderStatus, TradingMode
from dual_sleeve_trader.core.exchange_order import ExchangeOrderSnapshot
from dual_sleeve_trader.core.models import OrderRecord, SymbolFilters
from dual_sleeve_trader.ops import sleeve_b_auto_execute as auto_execute
from dual_sleeve_trader.ops.sleeve_b_auto_execute import (
    SleeveBAutoExecuteConfig,
    SleeveBAutoExecuteSafetyError,
    result_to_dict,
    run_sleeve_b_auto_execute,
)
from dual_sleeve_trader.strategies.sleeve_b_replay import OhlcBar


class FakeAutoExecuteExchange:
    def __init__(self, breakout: bool = True) -> None:
        self.breakout = breakout
        self.submitted: list[OrderRecord] = []

    def fetch_klines(self, symbol: str, interval: str, limit: int = 500) -> list[OhlcBar]:
        if interval == "1d":
            bars = [_bar(f"D{day:03d}", str(100 + day)) for day in range(1, 221)]
        elif interval == "4h":
            last_close = "105" if self.breakout else "100"
            bars = [_bar(f"B{index:03d}", "100", "101", "99") for index in range(121)] + [
                _bar("B121", last_close, "106", "104" if self.breakout else "99")
            ]
        elif interval == "1h":
            bars = [_bar(f"H{index:03d}", "104", "105", "103") for index in range(100)]
        else:
            bars = []
        return bars[-limit:]

    def fetch_account_snapshot(self) -> AccountSnapshotV3:
        return AccountSnapshotV3(
            total_wallet_balance=Decimal("10000"),
            total_unrealized_profit=Decimal("0"),
            total_margin_balance=Decimal("10000"),
            available_balance=Decimal("10000"),
        )

    def fetch_position_snapshots(self, symbol: str | None = None) -> list[ExchangePositionSnapshot]:
        return []

    def get_symbol_filters(self, symbol: str) -> SymbolFilters:
        return SymbolFilters(symbol, Decimal("0.1"), Decimal("0.001"), Decimal("50"))

    def submit_order(self, order: OrderRecord) -> OrderRecord:
        order.exchange_order_id = f"ex-{len(self.submitted) + 1}"
        order.status = OrderStatus.SUBMITTED
        self.submitted.append(order)
        return order

    def fetch_open_orders(self) -> list[OrderRecord]:
        return list(self.submitted)

    def query_order(self, symbol: str, client_order_id: str) -> ExchangeOrderSnapshot | None:
        _ = symbol
        for order in self.submitted:
            if order.client_order_id == client_order_id:
                return ExchangeOrderSnapshot(
                    client_order_id=order.client_order_id,
                    symbol=order.intent.symbol,
                    status=order.status,
                    exchange_order_id=order.exchange_order_id,
                    executed_quantity=order.filled_quantity,
                    average_price=order.average_fill_price,
                )
        return None


def _bar(timestamp: str, close: str, high: str | None = None, low: str | None = None) -> OhlcBar:
    close_decimal = Decimal(close)
    return OhlcBar(
        timestamp=timestamp,
        open=close_decimal,
        high=Decimal(high) if high is not None else close_decimal + Decimal("1"),
        low=Decimal(low) if low is not None else close_decimal - Decimal("1"),
        close=close_decimal,
    )


def _runtime(tmp_path) -> RuntimeConfig:
    return RuntimeConfig(
        trading_mode=TradingMode.EXCHANGE_TESTNET,
        exchange=ExchangeName.BINANCE_USDM_TESTNET,
        api_key="key",
        api_secret="secret",
        state_db_path=str(tmp_path / "state.sqlite3"),
    )


def test_auto_execute_requires_ack(tmp_path) -> None:
    with pytest.raises(SleeveBAutoExecuteSafetyError):
        run_sleeve_b_auto_execute(
            _runtime(tmp_path),
            SleeveBAutoExecuteConfig(acknowledge_testnet_order=False),
        )


def test_auto_execute_submits_one_order_and_reconciles(monkeypatch, tmp_path) -> None:
    fake_exchange = FakeAutoExecuteExchange(breakout=True)
    monkeypatch.setattr(auto_execute, "build_exchange_adapter", lambda runtime, allow_inert_fallback: fake_exchange)

    result = run_sleeve_b_auto_execute(
        _runtime(tmp_path),
        SleeveBAutoExecuteConfig(
            symbols=("BTCUSDT", "ETHUSDT"),
            max_new_orders_per_run=1,
            acknowledge_testnet_order=True,
        ),
    )

    assert result.ok
    assert result.candidates_scanned == 2
    assert result.loop_result.submitted_orders == 1
    assert len(fake_exchange.submitted) == 1
    payload = result_to_dict(result)
    assert payload["submitted_orders"] == 1
    assert payload["order_reconciliation"]["consistent"]
    assert payload["position_reconciliation"]["consistent"]


def test_auto_execute_no_candidates_no_orders(monkeypatch, tmp_path) -> None:
    fake_exchange = FakeAutoExecuteExchange(breakout=False)
    monkeypatch.setattr(auto_execute, "build_exchange_adapter", lambda runtime, allow_inert_fallback: fake_exchange)

    result = run_sleeve_b_auto_execute(
        _runtime(tmp_path),
        SleeveBAutoExecuteConfig(symbols=("BTCUSDT",), acknowledge_testnet_order=True),
    )

    assert result.ok
    assert result.candidates_scanned == 1
    assert result.loop_result.submitted_orders == 0
    assert fake_exchange.submitted == []
