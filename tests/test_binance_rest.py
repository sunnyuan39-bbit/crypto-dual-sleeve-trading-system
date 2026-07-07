from decimal import Decimal

import httpx

from dual_sleeve_trader.core.enums import OrderAction, OrderSide, OrderType, SleeveId
from dual_sleeve_trader.core.models import OrderIntent, OrderRecord
from dual_sleeve_trader.exchange.binance_rest import (
    BinanceCredentials,
    BinanceFuturesTestnetRestAdapter,
    parse_symbol_filters,
    sign_params,
)


def test_sign_params_uses_hmac_sha256() -> None:
    params = {
        "symbol": "BTCUSDT",
        "side": "BUY",
        "type": "LIMIT",
        "quantity": "1",
        "price": "9000",
        "timeInForce": "GTC",
        "recvWindow": 5000,
        "timestamp": 1591702613943,
    }
    signature = sign_params(params, "2b5eb11e18796d12d88f13dc27dbbd02c2cc51ff7059765ed9821957d82bb4d9")
    assert signature == "3c661234138461fcc7a7d8746c6558c9842d4e10870d2ecbedf7777cad694af9"


def test_parse_symbol_filters() -> None:
    parsed = parse_symbol_filters(
        {
            "symbol": "BTCUSDT",
            "filters": [
                {"filterType": "PRICE_FILTER", "tickSize": "0.10"},
                {"filterType": "LOT_SIZE", "stepSize": "0.001"},
                {"filterType": "MIN_NOTIONAL", "notional": "100"},
            ],
        }
    )
    assert parsed is not None
    assert parsed.symbol == "BTCUSDT"
    assert parsed.tick_size == Decimal("0.10")
    assert parsed.step_size == Decimal("0.001")
    assert parsed.min_notional == Decimal("100")


def test_loads_exchange_info_with_mock_transport() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/fapi/v1/exchangeInfo"
        return httpx.Response(
            200,
            json={
                "symbols": [
                    {
                        "symbol": "ETHUSDT",
                        "filters": [
                            {"filterType": "PRICE_FILTER", "tickSize": "0.01"},
                            {"filterType": "LOT_SIZE", "stepSize": "0.001"},
                            {"filterType": "MIN_NOTIONAL", "notional": "5"},
                        ],
                    }
                ]
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    adapter = BinanceFuturesTestnetRestAdapter(
        BinanceCredentials("key", "secret"),
        client=client,
    )
    filters = adapter.get_symbol_filters("ETHUSDT")
    assert filters.tick_size == Decimal("0.01")


def test_submit_order_sends_signed_testnet_request() -> None:
    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/fapi/v1/order"
        assert request.headers["X-MBX-APIKEY"] == "key"
        query = dict(request.url.params)
        seen.update(query)
        assert query["symbol"] == "BTCUSDT"
        assert query["newClientOrderId"] == "B_setup123_EN_20260101000000"
        assert "signature" in query
        return httpx.Response(
            200,
            json={
                "orderId": 123,
                "clientOrderId": query["newClientOrderId"],
                "status": "NEW",
                "executedQty": "0",
                "avgPrice": "0",
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    adapter = BinanceFuturesTestnetRestAdapter(
        BinanceCredentials("key", "secret"),
        client=client,
    )
    intent = OrderIntent(
        sleeve_id=SleeveId.B,
        symbol="BTCUSDT",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        action=OrderAction.ENTRY,
        quantity=Decimal("0.01"),
        price=Decimal("100000"),
        setup_id="setup12345678",
    )
    order = OrderRecord("B_setup123_EN_20260101000000", intent)
    result = adapter.submit_order(order)
    assert result.exchange_order_id == "123"
    assert seen["timeInForce"] == "GTC"
