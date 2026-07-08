# Binance Testnet Read/Write Smoke Test

PR-010 adds a gated Binance USD-M Futures Testnet read/write smoke test.

This is the first step that can submit a testnet order. It must only be used with Binance Testnet credentials.

## What it checks

The smoke test performs this sequence:

1. Read `exchangeInfo` through symbol filters.
2. Read account snapshot.
3. Read position snapshot.
4. Validate that the LIMIT order is non-marketable.
5. Submit one tiny testnet LIMIT order.
6. Query the order.
7. Cancel the order.
8. Query again and require `CANCELED`.
9. Run order reconciliation.
10. Refresh and run position reconciliation.
11. Confirm SAFE_MODE remains inactive.

## Safety gates

The script refuses to run unless all of these are true:

- `TRADING_MODE=EXCHANGE_TESTNET`
- `EXCHANGE=BINANCE_USDM_TESTNET`
- local testnet credentials are present
- `--i-understand-this-places-testnet-order` is passed
- order price passes the non-marketable guard

Do not use production API keys.

## Local `.env`

Create a local `.env` file. Do not commit it.

```env
TRADING_MODE=EXCHANGE_TESTNET
EXCHANGE=BINANCE_USDM_TESTNET
SMOKE_SYMBOL=BTCUSDT
STATE_DB_PATH=local_state.sqlite3
BINANCE_API_KEY=your_testnet_key
BINANCE_API_SECRET=your_testnet_secret
```

## Recommended BTCUSDT command

Choose a BUY limit price far below mark price so it should not fill.

Example:

```bash
python scripts/smoke_testnet_read_write.py \
  --symbol BTCUSDT \
  --side BUY \
  --quantity 0.01 \
  --limit-price 1000 \
  --i-understand-this-places-testnet-order
```

The default non-marketable guard requires:

- BUY limit price < `markPrice * 0.8`
- SELL limit price > `markPrice * 1.2`

## If the guard fails

Pick a more distant limit price.

For BUY:

```bash
--limit-price 1000
```

For SELL, choose a price far above mark price.

Do not use `--allow-marketable-test-order` unless manually debugging testnet behavior.

## Expected output

Successful output should include:

```json
{
  "ok": true,
  "submitted_status": "SUBMITTED",
  "queried_status_after_cancel": "CANCELED",
  "order_reconciliation_consistent": true,
  "position_reconciliation_consistent": true,
  "safe_mode_active": false
}
```

## Cleanup

If the script errors after submitting, manually check and cancel open testnet orders in Binance Testnet before running again.
