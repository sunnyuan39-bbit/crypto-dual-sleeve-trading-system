from decimal import Decimal

import httpx

from dual_sleeve_trader.exchange.binance_rest import (
    BinanceCredentials,
    BinanceFuturesTestnetRestAdapter,
    parse_account_snapshot,
    parse_position_snapshot,
)


def test_parse_account_snapshot() -> None:
    snapshot = parse_account_snapshot(
        {
            "totalWalletBalance": "1000.0",
            "totalUnrealizedProfit": "10.0",
            "totalMarginBalance": "1010.0",
            "availableBalance": "900.0",
            "assets": [
                {
                    "asset": "USDT",
                    "walletBalance": "1000.0",
                    "unrealizedProfit": "10.0",
                    "marginBalance": "1010.0",
                    "availableBalance": "900.0",
                    "updateTime": 123,
                }
            ],
        }
    )

    assert snapshot.total_wallet_balance == Decimal("1000.0")
    assert snapshot.assets[0].asset == "USDT"


def test_parse_position_snapshot_accepts_binance_fields() -> None:
    position = parse_position_snapshot(
        {
            "symbol": "BTCUSDT",
            "positionSide": "BOTH",
            "positionAmt": "0.5",
            "entryPrice": "100000",
            "markPrice": "101000",
            "unRealizedProfit": "500",
            "notional": "50500",
            "isolatedMargin": "0",
            "updateTime": 123,
        }
    )

    assert position.symbol == "BTCUSDT"
    assert position.position_amt == Decimal("0.5")
    assert position.unrealized_profit == Decimal("500")


def test_fetch_account_and_positions_use_signed_endpoints() -> None:
    seen_paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_paths.append(request.url.path)
        assert request.headers["X-MBX-APIKEY"] == "key"
        assert "signature" in dict(request.url.params)
        if request.url.path == "/fapi/v3/account":
            return httpx.Response(
                200,
                json={
                    "totalWalletBalance": "1000",
                    "totalUnrealizedProfit": "0",
                    "totalMarginBalance": "1000",
                    "availableBalance": "1000",
                    "assets": [],
                },
            )
        if request.url.path == "/fapi/v3/positionRisk":
            return httpx.Response(
                200,
                json=[
                    {
                        "symbol": "ETHUSDT",
                        "positionSide": "BOTH",
                        "positionAmt": "1",
                        "entryPrice": "2000",
                        "markPrice": "2010",
                        "unRealizedProfit": "10",
                        "notional": "2010",
                        "isolatedMargin": "0",
                    }
                ],
            )
        raise AssertionError(request.url.path)

    adapter = BinanceFuturesTestnetRestAdapter(
        BinanceCredentials("key", "secret"),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    account = adapter.fetch_account_snapshot()
    positions = adapter.fetch_position_snapshots()

    assert account.total_wallet_balance == Decimal("1000")
    assert positions[0].symbol == "ETHUSDT"
    assert seen_paths == ["/fapi/v3/account", "/fapi/v3/positionRisk"]
