from dual_sleeve_trader.exchange.binance_testnet import BinanceUsdmTestnetAdapter
from dual_sleeve_trader.execution.reconciliation import OrderReconciler
from dual_sleeve_trader.execution.reconciliation_runner import ReconciliationRunner
from dual_sleeve_trader.execution.safe_mode import SafeModeController
from dual_sleeve_trader.ops.alerts import ConsoleAlertSink
from dual_sleeve_trader.storage.sqlite_store import SQLiteOrderStore

store = SQLiteOrderStore("local_state.sqlite3")
safe_mode = SafeModeController()
exchange = BinanceUsdmTestnetAdapter()
reconciler = OrderReconciler(store, exchange, safe_mode)
result = ReconciliationRunner(reconciler, ConsoleAlertSink()).run_once()
print(result)
