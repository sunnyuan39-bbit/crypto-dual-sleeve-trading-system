from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class CapacitySnapshot:
    open_interest_usd: Decimal
    volume_24h_usd: Decimal
    entry_bid_depth_usd: Decimal
    exit_ask_depth_usd: Decimal


def capacity_check(
    notional: Decimal,
    snapshot: CapacitySnapshot,
    max_oi_share: Decimal = Decimal("0.005"),
    max_volume_share: Decimal = Decimal("0.002"),
    max_depth_share: Decimal = Decimal("0.5"),
) -> bool:
    if notional > max_oi_share * snapshot.open_interest_usd:
        return False
    if notional > max_volume_share * snapshot.volume_24h_usd:
        return False
    if notional > max_depth_share * snapshot.entry_bid_depth_usd:
        return False
    if notional > max_depth_share * snapshot.exit_ask_depth_usd:
        return False
    return True
