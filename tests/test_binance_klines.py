from decimal import Decimal

import httpx

from dual_sleeve_trader.exchange.binance_rest import (
    BinanceCredentials,
    BinanceFuturesTestnetRestAdapter,
    parse_kline,
)
from dual_sleeve_trader.strategies.sleeve_b_replay import OhlcBar


def test_parse_kline() -> None:
    payload = [1700000000000, "100", "110", "90", "105", "1234"]

    bar = parse_kline(payload)

    assert bar == OhlcBar("1700000000000", Decimal("100"), Decimal("110"), Decimal("90"), Decimal("105"))


def test_fetch_klines_calls_public_endpoint() -> None:
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url)
        return httpx.Response(
            200,
            json=[[1700000000000, "100", "110", "90", "105", "1234"]],
        )

    adapter = BinanceFuturesTestnetRestAdapter(
        BinanceCredentials("key", "secret"),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    bars = adapter.fetch_klines("BTCUSDT", "1h", 100)

    assert len(bars) == 1
    assert bars[0].close == Decimal("105")
    assert seen[0].path == "/fapi/v1/klines"
    assert "symbol=BTCUSDT" in str(seen[0])
    assert "interval=1h" in str(seen[0])
    assert "limit=100" in str(seen[0])
