# Sleeve B Auto Testnet Loop v0

PR-012 adds the first auto strategy execution loop for Sleeve B testnet trading.

This is an automated strategy path, but it is still deliberately gated.

## Flow

1. Build Sleeve B candidates from 1D and 4H OHLC bars.
2. Read account snapshot.
3. Read current positions.
4. Read exchange filters per symbol.
5. Run the PR-011 allocator.
6. Convert accepted allocation into a LIMIT `OrderIntent`.
7. Route through `OrderRouter` in `EXCHANGE_TESTNET` mode.
8. Persist submitted order through `PersistentOrderRouter`.
9. Stop after `max_new_orders_per_run` submissions.

## Symbol universe

The full Sleeve B universe may be scanned:

- BTCUSDT
- ETHUSDT
- SOLUSDT
- BNBUSDT
- HYPEUSDT

The loop does not blindly open all symbols. Allocator and execution gates still apply.

## Default execution gates

- requires explicit ACK via `SleeveBAutoLoopConfig(require_ack=True)`
- default `max_new_orders_per_run = 1`
- one position per symbol via allocator
- max concurrent positions via allocator
- portfolio margin cap via allocator
- per-position margin cap via allocator
- SAFE_MODE blocks new entries
- LIMIT orders only in this version

## Not included yet

- Binance kline fetching
- daemonized recurring scanner
- automatic stop-loss placement
- take-profit ladder placement
- time-stop exit orders
- Telegram alerts

Those should be added after the entry chain is stable.

## Safety note

This PR connects the strategy candidate path to testnet order routing, but it still requires an explicit in-code ACK and remains exchange-testnet only.
