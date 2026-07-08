from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN

from dual_sleeve_trader.core.account import AccountSnapshotV3, ExchangePositionSnapshot
from dual_sleeve_trader.core.enums import PositionSide
from dual_sleeve_trader.core.models import SymbolFilters
from dual_sleeve_trader.exchange.filters import floor_to_step, round_price_to_tick


@dataclass(frozen=True)
class SleeveBExecutionAllocatorConfig:
    symbols: tuple[str, ...] = ("BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "HYPEUSDT")
    usable_balance_fraction: Decimal = Decimal("0.5")
    max_portfolio_margin_fraction: Decimal = Decimal("0.5")
    max_per_position_margin_fraction: Decimal = Decimal("0.12")
    max_leverage: Decimal = Decimal("3")
    max_concurrent_positions: int = 3
    min_available_balance: Decimal = Decimal("500")
    default_risk_fraction_per_trade: Decimal = Decimal("0.01")


@dataclass(frozen=True)
class SleeveBSignalCandidate:
    symbol: str
    side: PositionSide
    entry_price: Decimal
    stop_price: Decimal
    setup_id: str

    @property
    def stop_distance(self) -> Decimal:
        return abs(self.entry_price - self.stop_price)


@dataclass(frozen=True)
class SleeveBAllocationDecision:
    accepted: bool
    symbol: str
    side: PositionSide
    quantity: Decimal
    entry_price: Decimal
    notional: Decimal
    initial_margin: Decimal
    leverage: Decimal
    risk_amount: Decimal
    reason: str


class SleeveBExecutionAllocator:
    def __init__(self, config: SleeveBExecutionAllocatorConfig | None = None) -> None:
        self.config = config or SleeveBExecutionAllocatorConfig()

    def allocate(
        self,
        candidate: SleeveBSignalCandidate,
        account: AccountSnapshotV3,
        positions: list[ExchangePositionSnapshot],
        filters: SymbolFilters,
    ) -> SleeveBAllocationDecision:
        if candidate.symbol not in self.config.symbols:
            return self._reject(candidate, "SYMBOL_NOT_ALLOWED")
        if account.available_balance < self.config.min_available_balance:
            return self._reject(candidate, "AVAILABLE_BALANCE_TOO_LOW")
        if candidate.stop_distance <= 0:
            return self._reject(candidate, "INVALID_STOP_DISTANCE")
        if _has_open_position(candidate.symbol, positions):
            return self._reject(candidate, "SYMBOL_ALREADY_HAS_POSITION")

        open_positions = [position for position in positions if not position.is_flat]
        if len(open_positions) >= self.config.max_concurrent_positions:
            return self._reject(candidate, "MAX_CONCURRENT_POSITIONS_REACHED")

        used_margin = _sum_initial_margin(open_positions, self.config.max_leverage)
        usable_balance = account.available_balance * self.config.usable_balance_fraction
        portfolio_margin_cap = usable_balance * self.config.max_portfolio_margin_fraction
        per_position_margin_cap = usable_balance * self.config.max_per_position_margin_fraction
        remaining_margin = portfolio_margin_cap - used_margin
        if remaining_margin <= 0:
            return self._reject(candidate, "PORTFOLIO_MARGIN_CAP_REACHED")

        allowed_margin = min(per_position_margin_cap, remaining_margin)
        allowed_notional = allowed_margin * self.config.max_leverage
        risk_budget = usable_balance * self.config.default_risk_fraction_per_trade
        risk_sized_quantity = risk_budget / candidate.stop_distance
        notional_sized_quantity = allowed_notional / candidate.entry_price
        raw_quantity = min(risk_sized_quantity, notional_sized_quantity)
        quantity = floor_to_step(raw_quantity, filters.step_size)
        entry_price = round_price_to_tick(candidate.entry_price, filters.tick_size)
        notional = quantity * entry_price

        if quantity <= 0:
            return self._reject(candidate, "QUANTITY_FLOORS_TO_ZERO")
        if notional < filters.min_notional:
            return self._reject(candidate, "BELOW_MIN_NOTIONAL")

        initial_margin = _quantize_usdt(notional / self.config.max_leverage)
        if initial_margin > allowed_margin:
            return self._reject(candidate, "MARGIN_EXCEEDS_ALLOWED_CAP")

        return SleeveBAllocationDecision(
            accepted=True,
            symbol=candidate.symbol,
            side=candidate.side,
            quantity=quantity,
            entry_price=entry_price,
            notional=_quantize_usdt(notional),
            initial_margin=initial_margin,
            leverage=self.config.max_leverage,
            risk_amount=_quantize_usdt(quantity * candidate.stop_distance),
            reason="ACCEPTED",
        )

    def _reject(self, candidate: SleeveBSignalCandidate, reason: str) -> SleeveBAllocationDecision:
        return SleeveBAllocationDecision(
            accepted=False,
            symbol=candidate.symbol,
            side=candidate.side,
            quantity=Decimal("0"),
            entry_price=candidate.entry_price,
            notional=Decimal("0"),
            initial_margin=Decimal("0"),
            leverage=self.config.max_leverage,
            risk_amount=Decimal("0"),
            reason=reason,
        )


def _has_open_position(symbol: str, positions: list[ExchangePositionSnapshot]) -> bool:
    return any(position.symbol == symbol and not position.is_flat for position in positions)


def _sum_initial_margin(positions: list[ExchangePositionSnapshot], leverage: Decimal) -> Decimal:
    total = Decimal("0")
    for position in positions:
        notional = abs(position.notional)
        if notional <= 0 and position.mark_price is not None:
            notional = abs(position.position_amt * position.mark_price)
        total += notional / leverage
    return total


def _quantize_usdt(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_DOWN)
