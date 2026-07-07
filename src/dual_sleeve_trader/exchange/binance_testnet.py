from __future__ import annotations

from decimal import Decimal

from dual_sleeve_trader.core.models import OrderRecord, SymbolFilters
from dual_sleeve_trader.exchange.interfaces import ExchangeAdapter


class BinanceUsdmTestnetAdapter(ExchangeAdapter):
    """Inert placeholder for Binance USD-M Futures Testnet integration."""

    def __init__(self, filters: dict[str, SymbolFilters] | None = None) -> None:
        self._filters = filters or {}
        self._orders: dict[str, OrderRecord] = {}

    def get_symbol_filters(self, symbol: str) -> SymbolFilters:
        return self._filters.get(
            symbol,
            SymbolFilters(
                symbol=symbol,
                tick_size=Decimal("0.01"),
                step_size=Decimal("0.001"),
                min_notional=Decimal("5"),
            ),
        )

    def submit_order(self, order: OrderRecord) -> OrderRecord:
        self._orders[order.client_order_id] = order
        return order

    def cancel_order(self, client_order_id: str, symbol: str) -> OrderRecord | None:
        _ = symbol
        return self._orders.pop(client_order_id, None)

    def fetch_open_orders(self) -> list[OrderRecord]:
        return list(self._orders.values())
