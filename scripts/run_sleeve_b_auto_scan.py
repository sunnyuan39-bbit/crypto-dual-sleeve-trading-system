from __future__ import annotations

import argparse
import json

from dual_sleeve_trader.config.runtime import load_runtime_config
from dual_sleeve_trader.exchange.factory import build_exchange_adapter
from dual_sleeve_trader.strategies.sleeve_b_candidate_builder import (
    SleeveBMarketData,
    build_sleeve_b_candidates,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Scan Sleeve B symbols with Binance klines.")
    parser.add_argument("--env-file", default=None)
    parser.add_argument("--symbols", default="BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT,HYPEUSDT")
    parser.add_argument("--daily-limit", type=int, default=250)
    parser.add_argument("--four-hour-limit", type=int, default=150)
    parser.add_argument("--one-hour-limit", type=int, default=100)
    parser.add_argument("--require-real-testnet", action="store_true")
    args = parser.parse_args()

    runtime = load_runtime_config(args.env_file)
    exchange = build_exchange_adapter(runtime, allow_inert_fallback=not args.require_real_testnet)
    symbols = [item.strip() for item in args.symbols.split(",") if item.strip()]
    market_data = []
    for symbol in symbols:
        market_data.append(
            SleeveBMarketData(
                symbol=symbol,
                daily_bars=tuple(exchange.fetch_klines(symbol, "1d", args.daily_limit)),
                four_hour_bars=tuple(exchange.fetch_klines(symbol, "4h", args.four_hour_limit)),
                one_hour_bars=tuple(exchange.fetch_klines(symbol, "1h", args.one_hour_limit)),
            )
        )

    results = build_sleeve_b_candidates(market_data)
    payload = [
        {
            "symbol": result.symbol,
            "has_candidate": result.candidate is not None,
            "reason": result.reason,
            "candidate": None
            if result.candidate is None
            else {
                "side": result.candidate.side.value,
                "entry_price": str(result.candidate.entry_price),
                "stop_price": str(result.candidate.stop_price),
                "setup_id": result.candidate.setup_id,
            },
        }
        for result in results
    ]
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
