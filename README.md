# 120K Dual-Sleeve Trading System

Production-oriented Python skeleton for a two-sleeve crypto strategy.

Safety defaults:

- Default mode: SIGNAL_ONLY
- Live trading: not implemented
- No API keys in repo
- Close orders must be reduce-only
- State mismatch triggers SAFE_MODE

Project layout:

- config: non-secret defaults
- core: enums and domain models
- exchange: exchange filters and adapters
- execution: router, state machine, safe mode, reconciliation, repair
- portfolio: virtual sleeve ledger
- risk: circuit breakers, freshness, overrides
- storage: local SQLite state
- strategies: sleeve B signals and sleeve A scanner guards
- ops: alert interfaces
- tests: production guardrail tests

Local setup:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
pytest
```

Environment:

Copy `.env.example` to `.env` locally. Never commit `.env`.

```bash
cp .env.example .env
```

Stage-gate intent:

1. Build execution skeleton and tests.
2. Run Sleeve B signal-only and historical replay.
3. Run Binance Futures Testnet / exchange simulation for one month.
4. Keep Sleeve A scanner-only until candidate quality, borrow proxy, depth, and cluster filters are validated.

Reconciliation and repair:

Local order state is persisted in SQLite. Reconciliation compares local open orders with exchange/testnet open orders and enters SAFE_MODE on mismatch. Repair queries an order by local clientOrderId, updates local status/fill fields from the exchange snapshot when ownership is known, and enters SAFE_MODE when manual review is required.
