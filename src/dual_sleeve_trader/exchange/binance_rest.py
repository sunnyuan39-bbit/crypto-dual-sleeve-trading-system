from __future__ import annotations

import hashlib
import hmac
import time
from dataclasses import dataclass
from decimal import Decimal
from typing import Any
from urllib.parse import urlencode

import httpx

from dual_sleeve_trader.core.enums import OrderStatus
from dual_sleeve_trader.core.models import OrderRecord, SymbolFilters
from dual_sleeve_trader.exchange.interfaces import ExchangeAdapter


BINANCE_USDM_TESTNET_BASE_URL = "https://demo-fapi.binance.com"


class BinanceApiError(RuntimeError):
    pass


@dataclass(frozen=True)
class BinanceCredentials:
    api_key: str
    api_secret: str


class BinanceFuturesTestnetRestAdapter(ExchangeAdapter):
    def __init__(
        self,
        credentials: BinanceCredentials,
        base_url: str = BINANCE_USDM_TESTNET_BASE_URL,
        recv_window: int = 5000,
        client: httpx.Client | None = None,
    ) -> None:
        if not credentials.api_key or not credentials.api_secret:
            raise ValueError("testnet credentials are required")
        self.credentials = credentials
        self.base_url = base_url.rstrip("/")
        self.recv_window = recv_window
        self.client = client or httpx.Client(timeout=10)
        self._filters_cache: dict[str, SymbolFilters] = {}

    def get_symbol_filters(self, symbol: str) -> SymbolFilters:
        if symbol not in self._filters_cache:
            self._load_exchange_info()
        try:
            return self._filters_cache[symbol]
        except KeyError as exc:
            raise BinanceApiError(f"symbol not found in exchangeInfo: {symbol}") from exc

    def submit_order(self, order: OrderRecord) -> OrderRecord:
        params: dict[str, Any] = {
            "symbol": order.intent.symbol,
            "side": order.intent.side.value,
            "type": order.intent.order_type.value,
            "quantity": format(order.intent.quantity, "f"),
            "newClientOrderId": order.client_order_id,
            "newOrderRespType": "RESULT",
        }
        if order.intent.price is not None:
            params["price"] = format(order.intent.price, "f")
            params["timeInForce"] = "GTC"
        if order.intent.reduce_only:
            params["reduceOnly"] = "true"

        payload = self._request("POST", "/fapi/v1/order", params=params, signed=True)
        return self._apply_exchange_order_payload(order, payload)

    def cancel_order(self, client_order_id: str, symbol: str) -> OrderRecord | None:
        payload = self._request(
            "DELETE",
            "/fapi/v1/order",
            params={"symbol": symbol, "origClientOrderId": client_order_id},
            signed=True,
        )
        return self._order_record_from_payload(payload)

    def fetch_open_orders(self) -> list[OrderRecord]:
        payload = self._request("GET", "/fapi/v1/openOrders", params={}, signed=True)
        if not isinstance(payload, list):
            raise BinanceApiError("expected list payload from openOrders")
        return [record for item in payload if (record := self._order_record_from_payload(item))]

    def _load_exchange_info(self) -> None:
        payload = self._request("GET", "/fapi/v1/exchangeInfo", params={}, signed=False)
        symbols = payload.get("symbols", []) if isinstance(payload, dict) else []
        filters: dict[str, SymbolFilters] = {}
        for symbol_info in symbols:
            parsed = parse_symbol_filters(symbol_info)
            if parsed is not None:
                filters[parsed.symbol] = parsed
        self._filters_cache = filters

    def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any],
        signed: bool,
    ) -> Any:
        request_params = dict(params)
        headers: dict[str, str] = {}
        if signed:
            headers["X-MBX-APIKEY"] = self.credentials.api_key
            request_params.setdefault("recvWindow", self.recv_window)
            request_params.setdefault("timestamp", int(time.time() * 1000))
            request_params["signature"] = sign_params(request_params, self.credentials.api_secret)

        response = self.client.request(
            method,
            f"{self.base_url}{path}",
            params=request_params,
            headers=headers,
        )
        if response.status_code >= 400:
            raise BinanceApiError(f"Binance API error {response.status_code}: {response.text}")
        return response.json()

    def _apply_exchange_order_payload(self, order: OrderRecord, payload: dict[str, Any]) -> OrderRecord:
        order.exchange_order_id = str(payload.get("orderId")) if payload.get("orderId") is not None else None
        status = payload.get("status")
        if status in _BINANCE_STATUS_MAP:
            order.status = _BINANCE_STATUS_MAP[status]
        executed_qty = payload.get("executedQty")
        avg_price = payload.get("avgPrice")
        if executed_qty is not None:
            order.filled_quantity = Decimal(str(executed_qty))
        if avg_price not in (None, "0", "0.0", "0.00000"):
            order.average_fill_price = Decimal(str(avg_price))
        return order

    def _order_record_from_payload(self, payload: dict[str, Any]) -> OrderRecord | None:
        # Open-order reconciliation will map exchange payloads back to local order records in PR-003.
        # This adapter deliberately avoids inventing sleeve ownership from exchange-only fields.
        _ = payload
        return None


_BINANCE_STATUS_MAP = {
    "NEW": OrderStatus.SUBMITTED,
    "PARTIALLY_FILLED": OrderStatus.PARTIALLY_FILLED,
    "FILLED": OrderStatus.FILLED,
    "CANCELED": OrderStatus.CANCELED,
    "REJECTED": OrderStatus.REJECTED,
    "EXPIRED": OrderStatus.EXPIRED,
}


def sign_params(params: dict[str, Any], api_secret: str) -> str:
    query = urlencode({key: value for key, value in params.items() if key != "signature"})
    return hmac.new(api_secret.encode(), query.encode(), hashlib.sha256).hexdigest()


def parse_symbol_filters(symbol_info: dict[str, Any]) -> SymbolFilters | None:
    symbol = symbol_info.get("symbol")
    raw_filters = symbol_info.get("filters", [])
    if not symbol or not isinstance(raw_filters, list):
        return None

    by_type = {item.get("filterType"): item for item in raw_filters if isinstance(item, dict)}
    price_filter = by_type.get("PRICE_FILTER", {})
    lot_size = by_type.get("LOT_SIZE", {})
    min_notional_filter = by_type.get("MIN_NOTIONAL", {}) or by_type.get("NOTIONAL", {})

    tick_size = Decimal(str(price_filter.get("tickSize", "0.01")))
    step_size = Decimal(str(lot_size.get("stepSize", "0.001")))
    min_notional = Decimal(
        str(
            min_notional_filter.get(
                "notional",
                min_notional_filter.get("minNotional", "5"),
            )
        )
    )
    return SymbolFilters(symbol=symbol, tick_size=tick_size, step_size=step_size, min_notional=min_notional)
