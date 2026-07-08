# Local Reconciliation Daemon

PR-008 adds a local daemon runner that wires together runtime config, exchange adapter, SQLite state, order reconciliation, position reconciliation, SAFE_MODE, and console alerts.

The daemon does not submit orders. It only reconciles local state against the configured simulation or testnet adapter.

## No-key dry run

```bash
python scripts/run_daemon.py --once
```

Expected behavior:

- Loads `.env` when present.
- Uses `INERT_TESTNET` by default.
- Creates the local SQLite DB path from `STATE_DB_PATH`.
- Runs one order reconciliation pass.
- Runs one position reconciliation pass.
- Prints JSON result.

## Loop mode

```bash
python scripts/run_daemon.py --interval-seconds 30 --max-iterations 10
```

This runs up to 10 iterations and stops early on mismatch by default.

## Continue on mismatch

```bash
python scripts/run_daemon.py --interval-seconds 30 --max-iterations 10 --continue-on-mismatch
```

This keeps running even if a mismatch enters SAFE_MODE.

## Real Binance USD-M Futures Testnet read mode

Create a local `.env` file. Do not commit it.

```env
TRADING_MODE=EXCHANGE_TESTNET
EXCHANGE=BINANCE_USDM_TESTNET
SMOKE_SYMBOL=BTCUSDT
STATE_DB_PATH=local_state.sqlite3
BINANCE_API_KEY=your_testnet_key
BINANCE_API_SECRET=your_testnet_secret
```

Run:

```bash
python scripts/run_daemon.py --once --require-real-testnet
```

Optional: refresh local positions from exchange before reconciliation.

```bash
python scripts/run_daemon.py --once --require-real-testnet --refresh-positions
```

## Safety rules

- Use testnet credentials only.
- Do not commit `.env`.
- Do not paste credentials into chat.
- The daemon does not submit orders.
- A mismatch enters SAFE_MODE.
