from decimal import Decimal

import pytest

from dual_sleeve_trader.core.account import AccountSnapshotV3, ExchangePositionSnapshot
from dual_sleeve_trader.core.enums import OrderSide, OrderStatus, TradingMode
from dual_sleeve_trader.core.exchange_order import ExchangeOrderSnapshot
from dual_sleeve_trader.core.models import OrderRecord, SymbolFilters
from dual_sleeve_trader.config.runtime import ExchangeName, RuntimeConfig
from dual_sleeve_trader.ops.testnet_read_write_smoke import (
    TestnetReadWriteSmokeResult,
    TestnetSmokeOrderConfig,
    TestnetSmokeSafetyError,
    result_to_dict,
    run_testnet_read_write_smoke,
    run_testnet_read_write_smoke_with_exchange,
)


class FakeReadWriteExchange:
    def __init__(self) -> None:
        self.submitted: OrderRecord | None = None
        self.canceled = False

    def get_symbol_filters(self, symbol: str) -> SymbolFilters:
        return SymbolFilters(symbol, Decimal("0.1"), Decimal("0.001"), Decimal("5"))

    def fetch_account_snapshot(self) -> AccountSnapshotV3:
        return AccountSnapshotV3(
            total_wallet_balance=Decimal("1000"),
            total_unrealized_profit=Decimal("0"),
            total_margin_balance=Decimal("1000"),
            available_balance=Decimal("1000"),
        )

    def fetch_position_snapshots(self, symbol: str | None = None) -> list[ExchangePositionSnapshot]:
        target = symbol or "BTCUSDT"
        return [
            ExchangePositionSnapshot(
                symbol=target,
                position_side="BOTH",
                position_amt=Decimal("0"),
                mark_price=Decimal("100000"),
            )
        ]

    def submit_order(self, order: OrderRecord) -> OrderRecord:
        order.exchange_order_id = "12345"
        order.status = OrderStatus.SUBMITTED
        self.submitted = order
        return order

    def query_order(self, symbol: str, client_order_id: str) -> ExchangeOrderSnapshot | None:
        assert self.submitted is not None
        assert symbol == self.submitted.intent.symbol
        assert client_order_id == self.submitted.client_order_id
        return ExchangeOrderSnapshot(
            client_order_id=client_order_id,
            symbol=symbol,
            status=OrderStatus.CANCELED if self.canceled else OrderStatus.SUBMITTED,
            exchange_order_id="12345",
            executed_quantity=Decimal("0"),
        )

    def cancel_order(self, client_order_id: str, symbol: str) -> OrderRecord | None:
        assert self.submitted is not None
        assert symbol == self.submitted.intent.symbol
        assert client_order_id == self.submitted.client_order_id
        self.canceled = True
        return None

    def fetch_open_orders(self) -> list[OrderRecord]:
        if self.submitted is None or self.canceled:
            return []
        return [self.submitted]


def test_read_write_smoke_requires_ack() -> None:
    with pytest.raises(TestnetSmokeSafetyError):
        run_testnet_read_write_smoke_with_exchange(
            FakeReadWriteExchange(),
            TestnetSmokeOrderConfig("BTCUSDT", OrderSide.BUY, Decimal("0.001"), Decimal("1000")),
            acknowledge_testnet_order=False,
        )


def test_read_write_smoke_blocks_marketable_buy() -> None:
    with pytest.raises(TestnetSmokeSafetyError):
        run_testnet_read_write_smoke_with_exchange(
            FakeReadWriteExchange(),
            TestnetSmokeOrderConfig("BTCUSDT", OrderSide.BUY, Decimal("0.001"), Decimal("90000")),
            acknowledge_testnet_order=True,
        )


def test_read_write_smoke_success() -> None:
    result = run_testnet_read_write_smoke_with_exchange(
        FakeReadWriteExchange(),
        TestnetSmokeOrderConfig("BTCUSDT", OrderSide.BUY, Decimal("0.01"), Decimal("1000")),
        acknowledge_testnet_order=True,
    )

    assert result.ok
    assert result.submitted_status == OrderStatus.SUBMITTED
    assert result.queried_status_after_cancel == OrderStatus.CANCELED
    assert result.order_reconciliation_consistent
    assert result.position_reconciliation_consistent
    assert not result.safe_mode_active


def test_runtime_validation_rejects_signal_only() -> None:
    runtime = RuntimeConfig(
        trading_mode=TradingMode.SIGNAL_ONLY,
        exchange=ExchangeName.INERT_TESTNET,
    )

    with pytest.raises(TestnetSmokeSafetyError):
        run_testnet_read_write_smoke(
            runtime,
            TestnetSmokeOrderConfig("BTCUSDT", OrderSide.BUY, Decimal("0.01"), Decimal("1000")),
            acknowledge_testnet_order=True,
        )


def test_result_to_dict() -> None:
    payload = result_to_dict(
        TestnetReadWriteSmokeResult(
            symbol="BTCUSDT",
            client_order_id="B_smoke_EN_20240101000000",
            exchange_order_id="12345",
            submitted_status=OrderStatus.SUBMITTED,
            queried_status_before_cancel=OrderStatus.SUBMITTED,
            queried_status_after_cancel=OrderStatus.CANCELED,
            order_reconciliation_consistent=True,
            position_reconciliation_consistent=True,
            safe_mode_active=False,
            account_total_wallet_balance=Decimal("1000"),
            position_count=1,
        )
    )

    assert payload["ok"] is True
    assert payload["queried_status_after_cancel"] == "CANCELED"
    assert payload["account_total_wallet_balance"] == "1000"
