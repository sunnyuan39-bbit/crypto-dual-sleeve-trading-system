from decimal import Decimal

import httpx

from dual_sleeve_trader.core.enums import OrderStatus
from dual_sleeve_trader.exchange.binance_rest import BinanceCredentials, BinanceFuturesTestnetRestAdapter


def test_query_order_by_client_id_uses_signed_endpoint() -> None:
    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/fapi/v1/order"
        assert request.headers["X-MBX-APIKEY"] == "key"
        query = dict(request.url.params)
        seen.update(query)
        assert query["symbol"] == "BTCUSDT"
        assert query["origClientOrderId"] == "B_setup123_EN_20260101000000"
        assert "timestamp" in query
        assert "signature" in query
        return httpx.Response(
            200,
            json={
                "symbol": "BTCUSDT",
                "orderId": 123,
                "clientOrderId": query["origClientOrderId"],
                "status": "FILLED",
                "executedQty": "0.01",
                "avgPrice": "100000.0",
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    adapter = BinanceFuturesTestnetRestAdapter(BinanceCredentials("key", "secret"), client=client)

    snapshot = adapter.query_order("BTCUSDT", "B_setup123_EN_20260101000000")

    assert snapshot is not None
    assert snapshot.status == OrderStatus.FILLED
    assert snapshot.exchange_order_id == "123"
    assert snapshot.executed_quantity == Decimal("0.01")
    assert snapshot.average_price == Decimal("100000.0")
    assert seen["recvWindow"] == "5000"
