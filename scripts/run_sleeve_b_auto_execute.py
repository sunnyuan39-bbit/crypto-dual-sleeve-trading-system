from __future__ import annotations

import argparse
import json

from dual_sleeve_trader.config.runtime import load_runtime_config
from dual_sleeve_trader.ops.sleeve_b_auto_execute import (
    SleeveBAutoExecuteConfig,
    result_to_dict,
    run_sleeve_b_auto_execute,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Sleeve B auto scan and ACK-gated testnet execution.")
    parser.add_argument("--env-file", default=None)
    parser.add_argument("--symbols", default="BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT,HYPEUSDT")
    parser.add_argument("--daily-limit", type=int, default=250)
    parser.add_argument("--four-hour-limit", type=int, default=150)
    parser.add_argument("--one-hour-limit", type=int, default=100)
    parser.add_argument("--max-new-orders-per-run", type=int, default=1)
    parser.add_argument("--i-understand-this-places-testnet-order", action="store_true")
    args = parser.parse_args()

    runtime = load_runtime_config(args.env_file)
    symbols = tuple(item.strip() for item in args.symbols.split(",") if item.strip())
    result = run_sleeve_b_auto_execute(
        runtime,
        SleeveBAutoExecuteConfig(
            symbols=symbols,
            daily_limit=args.daily_limit,
            four_hour_limit=args.four_hour_limit,
            one_hour_limit=args.one_hour_limit,
            max_new_orders_per_run=args.max_new_orders_per_run,
            acknowledge_testnet_order=args.i_understand_this_places_testnet_order,
        ),
    )
    print(json.dumps(result_to_dict(result), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
