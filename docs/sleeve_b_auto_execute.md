# Sleeve B Auto Execute CLI

PR-014 connects the read-only Sleeve B auto scan path to the ACK-gated testnet execution loop.

This is the first end-to-end auto testnet entry path:

1. Fetch 1D / 4H / 1H klines for the Sleeve B universe.
2. Build Sleeve B candidates.
3. Run the account-aware allocator.
4. Submit at most one LIMIT entry order to Binance USD-M testnet.
5. Persist the submitted order to SQLite.
6. Run order reconciliation.
7. Refresh and run position reconciliation.
8. Emit a JSON run report.

## Command

```bash
python scripts/run_sleeve_b_auto_execute.py \
  --i-understand-this-places-testnet-order
```

Custom symbol universe:

```bash
python scripts/run_sleeve_b_auto_execute.py \
  --symbols BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT,HYPEUSDT \
  --daily-limit 250 \
  --four-hour-limit 150 \
  --one-hour-limit 100 \
  --max-new-orders-per-run 1 \
  --i-understand-this-places-testnet-order
```

## Required environment

```bash
TRADING_MODE=EXCHANGE_TESTNET
EXCHANGE=BINANCE_USDM_TESTNET
BINANCE_API_KEY=...
BINANCE_API_SECRET=...
STATE_DB_PATH=local_state.sqlite3
```

## Safety gates

- Requires explicit CLI acknowledgement.
- Requires `TRADING_MODE=EXCHANGE_TESTNET`.
- Requires `EXCHANGE=BINANCE_USDM_TESTNET`.
- Requires testnet credentials.
- Uses the PR-011 allocator for testnet-sized positions.
- Defaults to `max_new_orders_per_run = 1`.
- Uses LIMIT entries only.
- SAFE_MODE blocks new entries.
- Reconciliation runs after the execution attempt.

## Not included yet

- Stop-loss order placement.
- Take-profit ladder placement.
- Time-stop exits.
- Recurring daemon schedule.
- Telegram notifications.

These should be added after the testnet entry path is stable.
