from __future__ import annotations

import hashlib
import hmac
import time
from dataclasses import dataclass
from decimal import Decimal
from typing import Any
from urllib.parse import urlencode

import httpx

from dual_sleeve_trader.core.account import AccountAssetSnapshot, AccountSnapshotV3, ExchangePositionSnapshot
from dual_sleeve_trader.core.enums import OrderStatus
from dual_sleeve_trader.core.exchange_order import ExchangeOrderSnapshot
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
        _ = payload
        return None

    def fetch_open_orders(self) -> list[OrderRecord]:
        payload = self._request("GET", "/fapi/v1/openOrders", params={}, signed=True)
        if not isinstance(payload, list):
            raise BinanceApiError("expected list payload from openOrders")
        return []

    def query_order(self, symbol: str, client_order_id: str) -> ExchangeOrderSnapshot | None:
        payload = self._request(
            "GET",
            "/fapi/v1/order",
            params={"symbol": symbol, "origClientOrderId": client_order_id},
            signed=True,
        )
        if not isinstance(payload, dict):
            raise BinanceApiError("expected object payload from query order")
        return parse_order_snapshot(payload)

    def fetch_account_snapshot(self) -> AccountSnapshotV3:
        payload = self._request("GET", "/fapi/v3/account", params={}, signed=True)
        if not isinstance(payload, dict):
            raise BinanceApiError("expected object payload from account snapshot")
        return parse_account_snapshot(payload)

    def fetch_position_snapshots(self, symbol: str | None = None) -> list[ExchangePositionSnapshot]:
        params = {"symbol": symbol} if symbol else {}
        payload = self._request("GET", "/fapi/v3/positionRisk", params=params, signed=True)
        if not isinstance(payload, list):
            raise BinanceApiError("expected list payload from positionRisk")
        return [parse_position_snapshot(item) for item in payload if isinstance(item, dict)]

    def fetch_mark_price(self, symbol: str) -> Decimal:
        payload = self._request("GET", "/fapi/v1/premiumIndex", params={"symbol": symbol}, signed=False)
        if not isinstance(payload, dict):
            raise BinanceApiError("expected object payload from premiumIndex")
        return parse_mark_price(payload)

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


def parse_account_snapshot(payload: dict[str, Any]) -> AccountSnapshotV3:
    assets = tuple(
        AccountAssetSnapshot(
            asset=str(item.get("asset")),
            wallet_balance=Decimal(str(item.get("walletBalance", "0"))),
            unrealized_profit=Decimal(str(item.get("unrealizedProfit", "0"))),
            margin_balance=Decimal(str(item.get("marginBalance", "0"))),
            available_balance=Decimal(str(item["availableBalance"])) if item.get("availableBalance") is not None else None,
            update_time_ms=int(item["updateTime"]) if item.get("updateTime") is not None else None,
        )
        for item in payload.get("assets", [])
        if isinstance(item, dict)
    )
    return AccountSnapshotV3(
        total_wallet_balance=Decimal(str(payload.get("totalWalletBalance", "0"))),
        total_unrealized_profit=Decimal(str(payload.get("totalUnrealizedProfit", "0"))),
        total_margin_balance=Decimal(str(payload.get("totalMarginBalance", "0"))),
        available_balance=Decimal(str(payload.get("availableBalance", "0"))),
        assets=assets,
    )


def parse_position_snapshot(payload: dict[str, Any]) -> ExchangePositionSnapshot:
    return ExchangePositionSnapshot(
        symbol=str(payload.get("symbol")),
        position_side=str(payload.get("positionSide", "BOTH")),
        position_amt=Decimal(str(payload.get("positionAmt", "0"))),
        entry_price=Decimal(str(payload["entryPrice"])) if payload.get("entryPrice") is not None else None,
        mark_price=Decimal(str(payload["markPrice"])) if payload.get("markPrice") is not None else None,
        unrealized_profit=Decimal(str(payload.get("unRealizedProfit", payload.get("unrealizedProfit", "0")))),
        notional=Decimal(str(payload.get("notional", "0"))),
        isolated_margin=Decimal(str(payload.get("isolatedMargin", "0"))),
        update_time_ms=int(payload["updateTime"]) if payload.get("updateTime") is not None else None,
    )


def parse_mark_price(payload: dict[str, Any]) -> Decimal:
    mark_price = payload.get("markPrice")
    if mark_price is None:
        raise BinanceApiError("premiumIndex payload missing markPrice")
    return Decimal(str(mark_price))


def parse_order_snapshot(payload: dict[str, Any]) -> ExchangeOrderSnapshot:
    status = _BINANCE_STATUS_MAP.get(str(payload.get("status")), OrderStatus.UNKNOWN)
    avg_price_raw = payload.get("avgPrice")
    average_price = None if avg_price_raw in (None, "0", "0.0", "0.00000") else Decimal(str(avg_price_raw))
    return ExchangeOrderSnapshot(
        client_order_id=str(payload.get("clientOrderId")),
        symbol=str(payload.get("symbol")),
        status=status,
        exchange_order_id=str(payload.get("orderId")) if payload.get("orderId") is not None else None,
        executed_quantity=Decimal(str(payload.get("executedQty", "0")),),
        average_price=average_price,
    )


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
