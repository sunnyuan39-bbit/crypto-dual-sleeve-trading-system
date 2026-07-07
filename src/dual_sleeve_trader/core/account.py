from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class AccountAssetSnapshot:
    asset: str
    wallet_balance: Decimal
    unrealized_profit: Decimal
    margin_balance: Decimal
    available_balance: Decimal | None = None
    update_time_ms: int | None = None


@dataclass(frozen=True)
class AccountSnapshotV3:
    total_wallet_balance: Decimal
    total_unrealized_profit: Decimal
    total_margin_balance: Decimal
    available_balance: Decimal
    assets: tuple[AccountAssetSnapshot, ...] = ()


@dataclass(frozen=True)
class ExchangePositionSnapshot:
    symbol: str
    position_side: str
    position_amt: Decimal
    entry_price: Decimal | None = None
    mark_price: Decimal | None = None
    unrealized_profit: Decimal = Decimal("0")
    notional: Decimal = Decimal("0")
    isolated_margin: Decimal = Decimal("0")
    update_time_ms: int | None = None

    @property
    def is_flat(self) -> bool:
        return self.position_amt == 0

    @property
    def key(self) -> tuple[str, str]:
        return (self.symbol, self.position_side)
