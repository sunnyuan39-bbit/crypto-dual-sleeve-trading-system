from __future__ import annotations

from datetime import UTC, datetime

from dual_sleeve_trader.core.enums import OrderAction, SleeveId


def make_client_order_id(
    sleeve_id: SleeveId,
    setup_id: str,
    action: OrderAction,
    now: datetime | None = None,
) -> str:
    timestamp = (now or datetime.now(tz=UTC)).strftime("%Y%m%d%H%M%S")
    prefix = setup_id[:8]
    return "_".join([sleeve_id.value, prefix, action.value, timestamp])
