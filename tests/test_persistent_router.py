from decimal import Decimal

from dual_sleeve_trader.core.enums import OrderAction, OrderSide, OrderType, SleeveId, TradingMode
from dual_sleeve_trader.core.models import OrderIntent
from dual_sleeve_trader.exchange.binance_testnet import BinanceUsdmTestnetAdapter
from dual_sleeve_trader.execution.order_router import OrderRouter
from dual_sleeve_trader.execution.persistent_router import PersistentOrderRouter
from dual_sleeve_trader.execution.safe_mode import SafeModeController
from dual_sleeve_trader.storage.sqlite_store import SQLiteOrderStore


def test_persistent_router_saves_submitted_order(tmp_path) -> None:
    store = SQLiteOrderStore(tmp_path / "state.sqlite3")
    router = OrderRouter(TradingMode.EXCHANGE_TESTNET, BinanceUsdmTestnetAdapter(), SafeModeController())
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

    result = PersistentOrderRouter(router, store).route(intent)

    assert result.accepted
    assert result.order is not None
    assert store.get_order(result.order.client_order_id) is not None
