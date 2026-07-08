from decimal import Decimal

from dual_sleeve_trader.core.account import AccountSnapshotV3, ExchangePositionSnapshot
from dual_sleeve_trader.core.enums import OrderStatus, PositionSide
from dual_sleeve_trader.core.models import OrderRecord, SymbolFilters
from dual_sleeve_trader.execution.safe_mode import SafeModeController
from dual_sleeve_trader.execution.sleeve_b_allocator import SleeveBSignalCandidate
from dual_sleeve_trader.execution.sleeve_b_testnet_loop import SleeveBAutoLoopConfig, SleeveBAutoTestnetLoop
from dual_sleeve_trader.storage.sqlite_store import SQLiteOrderStore
from dual_sleeve_trader.strategies.sleeve_b_candidate_builder import (
    SleeveBMarketData,
    build_sleeve_b_candidate,
)
from dual_sleeve_trader.strategies.sleeve_b_replay import OhlcBar


class FakeLoopExchange:
    def __init__(self) -> None:
        self.submitted: list[OrderRecord] = []

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


def _bar(timestamp: str, close: str, high: str | None = None, low: str | None = None) -> OhlcBar:
    close_decimal = Decimal(close)
    return OhlcBar(
        timestamp=timestamp,
        open=close_decimal,
        high=Decimal(high) if high is not None else close_decimal + Decimal("1"),
        low=Decimal(low) if low is not None else close_decimal - Decimal("1"),
        close=close_decimal,
    )


def _candidate(symbol: str = "BTCUSDT") -> SleeveBSignalCandidate:
    return SleeveBSignalCandidate(
        symbol=symbol,
        side=PositionSide.LONG,
        entry_price=Decimal("100000"),
        stop_price=Decimal("99000"),
        setup_id=f"auto-{symbol.lower()}",
    )


def test_candidate_builder_builds_long_breakout_candidate() -> None:
    daily = tuple(_bar(f"2023-D{day:03d}", str(100 + day)) for day in range(1, 221))
    four_hour = tuple([_bar(f"2024-B{index:03d}", "100", "101", "99") for index in range(121)] + [_bar("2024-B121", "105", "106", "104")])

    result = build_sleeve_b_candidate(SleeveBMarketData("BTCUSDT", daily, four_hour))

    assert result.candidate is not None
    assert result.candidate.symbol == "BTCUSDT"
    assert result.candidate.side == PositionSide.LONG
    assert result.candidate.stop_price < result.candidate.entry_price


def test_auto_loop_requires_ack(tmp_path) -> None:
    exchange = FakeLoopExchange()
    store = SQLiteOrderStore(tmp_path / "orders.sqlite3")
    loop = SleeveBAutoTestnetLoop(
        exchange,
        store,
        SafeModeController(),
        config=SleeveBAutoLoopConfig(require_ack=False),
    )

    result = loop.run_once([_candidate()])

    assert result.submitted_orders == 0
    assert result.decisions[0].reason == "ACK_REQUIRED"
    assert exchange.submitted == []


def test_auto_loop_submits_at_most_one_order_and_persists(tmp_path) -> None:
    exchange = FakeLoopExchange()
    store = SQLiteOrderStore(tmp_path / "orders.sqlite3")
    loop = SleeveBAutoTestnetLoop(
        exchange,
        store,
        SafeModeController(),
        config=SleeveBAutoLoopConfig(require_ack=True, max_new_orders_per_run=1),
    )

    result = loop.run_once([_candidate("BTCUSDT"), _candidate("ETHUSDT")])

    assert result.submitted_orders == 1
    assert result.decisions[0].accepted
    assert result.decisions[1].reason == "MAX_NEW_ORDERS_PER_RUN_REACHED"
    open_orders = store.list_open_orders()
    assert len(open_orders) == 1
    assert open_orders[0].intent.symbol == "BTCUSDT"
