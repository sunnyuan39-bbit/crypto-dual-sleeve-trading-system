# Sleeve B Testnet Execution Allocator

PR-011 adds an account-aware allocator for Sleeve B testnet execution.

The production Sleeve B design assumes an 80,000 USDT sleeve. Binance testnet accounts usually have a much smaller available balance, often around 5,000-10,000 USDT. This allocator therefore sizes from the actual account snapshot instead of the production sleeve value.

## Symbols

The allocator allows the full Sleeve B symbol universe to be scanned:

- BTCUSDT
- ETHUSDT
- SOLUSDT
- BNBUSDT
- HYPEUSDT

Scanning all symbols does not mean opening all symbols. Every accepted candidate must pass margin and position gates.

## Default gates

- `usable_balance_fraction = 0.5`
- `max_portfolio_margin_fraction = 0.5`
- `max_per_position_margin_fraction = 0.12`
- `max_leverage = 3x`
- `max_concurrent_positions = 3`
- `default_risk_fraction_per_trade = 1% of usable balance`
- no pyramiding: one position per symbol

## Example with 10,000 USDT available

- usable balance = 5,000
- portfolio margin cap = 2,500
- per-position margin cap = 600
- with 3x leverage, max notional per new position is about 1,800
- up to 3 concurrent positions, also constrained by portfolio margin cap

## Example with 5,000 USDT available

- usable balance = 2,500
- portfolio margin cap = 1,250
- per-position margin cap = 300
- with 3x leverage, max notional per new position is about 900
- up to 3 concurrent positions, but portfolio margin usually becomes the binding constraint

## Rejection reasons

The allocator can reject a signal candidate for these reasons:

- `SYMBOL_NOT_ALLOWED`
- `AVAILABLE_BALANCE_TOO_LOW`
- `INVALID_STOP_DISTANCE`
- `SYMBOL_ALREADY_HAS_POSITION`
- `MAX_CONCURRENT_POSITIONS_REACHED`
- `PORTFOLIO_MARGIN_CAP_REACHED`
- `QUANTITY_FLOORS_TO_ZERO`
- `BELOW_MIN_NOTIONAL`
- `MARGIN_EXCEEDS_ALLOWED_CAP`

## Safety notes

- This allocator does not submit orders.
- It only calculates whether a Sleeve B signal may be routed.
- Order submission remains gated by the execution loop and existing testnet mode checks.
- The allocator uses exchange filters for tick size, step size, and min notional.
