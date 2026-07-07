# Testnet Smoke Run

The smoke runner supports two modes.

## No-key mode

```bash
python scripts/smoke_testnet.py
```

This uses the inert adapter and does not call Binance.

## Real testnet read mode

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

The smoke runner reads exchange filters, account snapshot, and position snapshot when available. It does not submit orders.

Safety rules:

- Use testnet credentials only.
- Do not commit `.env`.
- Do not paste credentials into chat.
- Rotate the key after testing if needed.
