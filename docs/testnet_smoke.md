# Testnet Smoke Run

This smoke runner is designed for local Binance USD-M Futures Testnet checks only. Do not use real production exchange keys.

## No-key mock mode

This mode uses the inert adapter and does not call Binance.

```bash
python scripts/smoke_testnet.py
```

Expected behavior:

- Reads `.env` if present.
- Falls back to `INERT_TESTNET` if no real testnet credentials are configured.
- Prints symbol filter checks.
- Does not submit orders.

## Real Binance USD-M Futures Testnet mode

Create a local `.env` file. Do not commit it.

```env
TRADING_MODE=EXCHANGE_TESTNET
EXCHANGE=BINANCE_USDM_TESTNET
SMOKE_SYMBOL=BTCUSDT
BINANCE_API_KEY=your_testnet_key
BINANCE_API_SECRET=your_testnet_secret
```

Run:

```bash
python scripts/smoke_testnet.py --require-real-testnet
```

Expected behavior:

- Loads credentials only from your local `.env` or shell environment.
- Calls Binance testnet read endpoints.
- Reads exchange filters.
- Reads account and position snapshots when supported.
- Does not submit orders.

## Safety rules

- Never paste API keys into ChatGPT.
- Never commit `.env`.
- Use testnet credentials only.
- Disable withdrawal permissions on any key you create.
- Rotate/delete the key after testing if needed.
