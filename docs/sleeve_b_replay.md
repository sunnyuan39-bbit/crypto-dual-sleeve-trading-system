# Sleeve B Historical Replay

PR-009 adds a local historical replay runner for Sleeve B. It is designed to validate strategy logic before any testnet read/write test.

The replay runner does not call Binance and does not submit orders.

## Strategy logic in this replay

- Daily regime filter:
  - `BULL` when last daily close > EMA50 > EMA200
  - `BEAR` when last daily close < EMA50 < EMA200
  - otherwise no entry
- 4H entry:
  - long: close breaks above prior Donchian high
  - short: close breaks below prior Donchian low
- Initial stop:
  - `2.5 * ATR(14)` from entry price
- Position sizing:
  - risk budget defaults to `R = 800 USDT`
  - capped by `sleeve_equity * max_leverage`
- Take profit ladder:
  - TP1 at 1.5R, closes 30%
  - TP2 at 2.5R, closes 30%
  - TP3 at 4R, closes remaining 40%
- Stop management:
  - after TP1, stop moves to breakeven
- Time stop:
  - defaults to 12 four-hour bars, roughly 48 hours

## CSV format

Both daily and 4H CSV files must use this header:

```csv
timestamp,open,high,low,close
2024-01-01T00:00:00,100,110,90,105
```

Timestamps are treated as sortable strings. Use ISO-like timestamps or another lexicographically sortable format.

## Run example

```bash
python scripts/run_sleeve_b_replay.py \
  --symbol BTCUSDT \
  --daily-csv data/BTCUSDT_1d.csv \
  --four-hour-csv data/BTCUSDT_4h.csv
```

Override risk parameters:

```bash
python scripts/run_sleeve_b_replay.py \
  --symbol ETHUSDT \
  --daily-csv data/ETHUSDT_1d.csv \
  --four-hour-csv data/ETHUSDT_4h.csv \
  --unit-r 800 \
  --sleeve-equity 80000 \
  --max-leverage 5 \
  --time-stop-bars 12
```

## Output

The script prints JSON with:

- summary
- trades
- entry and exit price
- exit reason
- realized PnL
- gross R
- TP hits
- max drawdown

## Safety notes

- No exchange credentials are required.
- No testnet calls are made.
- No orders are submitted.
- This is strategy logic validation only.
