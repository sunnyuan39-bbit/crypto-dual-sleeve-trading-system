# 120K Dual-Sleeve Trading System

Production-oriented Python skeleton for a two-sleeve crypto strategy:

- **Sleeve B**: major-coin beta trend sleeve.
- **Sleeve A**: small-cap crash-confirmation short scanner.

The first milestone is **exchange simulation / testnet trial only**. Live trading is deliberately disabled by default and should remain locked until the testnet stage-gate is passed.

## Safety defaults

- Default mode: `SIGNAL_ONLY`
- Live trading: not implemented
- No API keys in repo
- All close orders must be `reduce_only=True`
- State mismatch should trigger `SAFE_MODE`
- Manual override has higher priority than strategy signals

## Project layout

```text
config/                         # non-secret defaults
src/dual_sleeve_trader/
  core/                         # enums and dataclasses
  exchange/                     # exchange filters and adapter interfaces
  execution/                    # router, state machine, safe mode
  portfolio/                    # virtual sleeve ledger
  risk/                         # circuit breakers, freshness, overrides
  strategies/                   # sleeve B signal and sleeve A scanner skeletons
  ops/                          # alert interfaces
tests/                          # unit tests for production guardrails
```

## Local setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
pytest
```

## Environment

Copy `.env.example` to `.env` locally. Never commit `.env`.

```bash
cp .env.example .env
```

## Stage-gate intent

1. Build execution skeleton and tests.
2. Run Sleeve B signal-only and historical replay.
3. Run Binance Futures Testnet / exchange simulation for one month.
4. Keep Sleeve A scanner-only until candidate quality, borrow proxy, depth, and cluster filters are validated.
