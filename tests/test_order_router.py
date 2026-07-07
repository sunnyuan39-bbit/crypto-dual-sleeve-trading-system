from decimal import Decimal

from dual_sleeve_trader.core.enums import OrderAction, OrderSide, OrderType, SleeveId, TradingMode
from dual_sleeve_trader.core.models import OrderIntent
from dual_sleeve_trader.exchange.binance_testnet import BinanceUsdmTestnetAdapter
from dual_sleeve_trader.execution.order_router import OrderRouter
from dual_sleeve_trader.execution.safe_mode import SafeModeController


def test_signal_only_accepts_but_does_not_submit() -> None:
    router = OrderRouter(
        TradingMode.SIGNAL_ONLY,
        BinanceUsdmTestnetAdapter(),
        SafeModeController(),
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
    result = router.route(intent)
    assert result.accepted
    assert result.reason == "SIGNAL_ONLY_NO_SUBMIT"
    assert router.exchange.fetch_open_orders() == []


def test_close_order_must_be_reduce_only() -> None:
    router = OrderRouter(
        TradingMode.EXCHANGE_TESTNET,
        BinanceUsdmTestnetAdapter(),
        SafeModeController(),
    )
    intent = OrderIntent(
        sleeve_id=SleeveId.B,
        symbol="BTCUSDT",
        side=OrderSide.SELL,
        order_type=OrderType.MARKET,
        action=OrderAction.STOP_LOSS,
        quantity=Decimal("0.01"),
        setup_id="setup12345678",
    )
    result = router.route(intent)
    assert not result.accepted
    assert result.reason == "CLOSE_ORDER_MUST_BE_REDUCE_ONLY"
