from decimal import Decimal

from dual_sleeve_trader.core.account import AccountSnapshotV3, ExchangePositionSnapshot
from dual_sleeve_trader.core.enums import PositionSide
from dual_sleeve_trader.core.models import SymbolFilters
from dual_sleeve_trader.execution.sleeve_b_allocator import (
    SleeveBExecutionAllocator,
    SleeveBExecutionAllocatorConfig,
    SleeveBSignalCandidate,
)


def _account(available: str) -> AccountSnapshotV3:
    return AccountSnapshotV3(
        total_wallet_balance=Decimal(available),
        total_unrealized_profit=Decimal("0"),
        total_margin_balance=Decimal(available),
        available_balance=Decimal(available),
    )


def _filters(symbol: str = "BTCUSDT") -> SymbolFilters:
    return SymbolFilters(symbol, Decimal("0.1"), Decimal("0.001"), Decimal("50"))


def _candidate(symbol: str = "BTCUSDT") -> SleeveBSignalCandidate:
    return SleeveBSignalCandidate(
        symbol=symbol,
        side=PositionSide.LONG,
        entry_price=Decimal("100000"),
        stop_price=Decimal("99000"),
        setup_id="btest001",
    )


def test_allocator_accepts_btc_with_10k_testnet_balance() -> None:
    allocator = SleeveBExecutionAllocator()

    decision = allocator.allocate(_candidate(), _account("10000"), [], _filters())

    assert decision.accepted
    assert decision.quantity > 0
    assert decision.notional <= Decimal("1800")
    assert decision.initial_margin <= Decimal("600")
    assert decision.leverage == Decimal("3")


def test_allocator_scales_down_for_5k_testnet_balance() -> None:
    allocator = SleeveBExecutionAllocator()

    decision = allocator.allocate(_candidate(), _account("5000"), [], _filters())

    assert decision.accepted
    assert decision.notional <= Decimal("900")
    assert decision.initial_margin <= Decimal("300")


def test_allocator_rejects_symbol_already_open() -> None:
    allocator = SleeveBExecutionAllocator()
    positions = [
        ExchangePositionSnapshot(
            symbol="BTCUSDT",
            position_side="BOTH",
            position_amt=Decimal("0.01"),
            mark_price=Decimal("100000"),
            notional=Decimal("1000"),
        )
    ]

    decision = allocator.allocate(_candidate(), _account("10000"), positions, _filters())

    assert not decision.accepted
    assert decision.reason == "SYMBOL_ALREADY_HAS_POSITION"


def test_allocator_rejects_when_max_positions_reached() -> None:
    allocator = SleeveBExecutionAllocator(
        SleeveBExecutionAllocatorConfig(max_concurrent_positions=2)
    )
    positions = [
        ExchangePositionSnapshot("ETHUSDT", "BOTH", Decimal("1"), mark_price=Decimal("3000"), notional=Decimal("3000")),
        ExchangePositionSnapshot("SOLUSDT", "BOTH", Decimal("10"), mark_price=Decimal("150"), notional=Decimal("1500")),
    ]

    decision = allocator.allocate(_candidate(), _account("10000"), positions, _filters())

    assert not decision.accepted
    assert decision.reason == "MAX_CONCURRENT_POSITIONS_REACHED"


def test_allocator_rejects_below_min_notional() -> None:
    allocator = SleeveBExecutionAllocator(
        SleeveBExecutionAllocatorConfig(default_risk_fraction_per_trade=Decimal("0.0001"))
    )

    decision = allocator.allocate(_candidate(), _account("5000"), [], _filters())

    assert not decision.accepted
    assert decision.reason == "BELOW_MIN_NOTIONAL"


def test_allocator_rejects_disallowed_symbol() -> None:
    allocator = SleeveBExecutionAllocator()

    decision = allocator.allocate(_candidate("DOGEUSDT"), _account("10000"), [], _filters("DOGEUSDT"))

    assert not decision.accepted
    assert decision.reason == "SYMBOL_NOT_ALLOWED"
