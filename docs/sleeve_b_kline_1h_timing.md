# Sleeve B Kline Fetcher and 1H Timing Filter

PR-013 adds Binance kline fetching and a 1H execution timing filter for Sleeve B.

## Timeframe roles

- 1D: regime filter
  - EMA50 / EMA200
  - BULL / BEAR / CHOP
- 4H: primary signal
  - Donchian breakout / breakdown
  - ATR stop basis
- 1H: execution timing refinement
  - avoid chasing overextended breakout candles
  - avoid entering against a strong reversal candle
  - refine the LIMIT entry price

## Default bar counts

- 1D: 250 bars
- 4H: 150 bars
- 1H: 100 bars

## 1H filter rules

For LONG candidates:

- reject if latest 1H close is below 1H EMA20
- reject if latest 1H candle is a strong bearish reversal
- reject if latest 1H close is more than 1.5 * 1H ATR above EMA20
- refine entry price to the lower of 4H close and latest 1H close minus 5 bps

For SHORT candidates:

- reject if latest 1H close is above 1H EMA20
- reject if latest 1H candle is a strong bullish reversal
- reject if latest 1H close is more than 1.5 * 1H ATR below EMA20
- refine entry price to the higher of 4H close and latest 1H close plus 5 bps

## Scan command

Read-only scan, no orders submitted:

```bash
python scripts/run_sleeve_b_auto_scan.py \
  --require-real-testnet
```

Custom symbols:

```bash
python scripts/run_sleeve_b_auto_scan.py \
  --symbols BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT,HYPEUSDT \
  --daily-limit 250 \
  --four-hour-limit 150 \
  --one-hour-limit 100 \
  --require-real-testnet
```

The scan command only prints candidate results. It does not submit orders.

## Safety notes

- This PR does not add recurring daemon execution.
- This PR does not place stop-loss or take-profit orders.
- This PR does not submit orders from the scan CLI.
- Order routing remains in PR-012's explicit ACK-gated loop.
