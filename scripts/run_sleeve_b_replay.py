from __future__ import annotations

import argparse
import json
from decimal import Decimal

from dual_sleeve_trader.strategies.sleeve_b_replay import (
    SleeveBReplayConfig,
    load_ohlc_csv,
    run_sleeve_b_replay,
)


def _decimal_default(value: object) -> str:
    if isinstance(value, Decimal):
        return str(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Sleeve B historical replay from local CSV files.")
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--daily-csv", required=True)
    parser.add_argument("--four-hour-csv", required=True)
    parser.add_argument("--unit-r", default="800")
    parser.add_argument("--sleeve-equity", default="80000")
    parser.add_argument("--max-leverage", default="5")
    parser.add_argument("--time-stop-bars", type=int, default=12)
    args = parser.parse_args()

    config = SleeveBReplayConfig(
        unit_r=Decimal(args.unit_r),
        sleeve_equity=Decimal(args.sleeve_equity),
        max_leverage=Decimal(args.max_leverage),
        time_stop_bars=args.time_stop_bars,
    )
    result = run_sleeve_b_replay(
        args.symbol,
        load_ohlc_csv(args.daily_csv),
        load_ohlc_csv(args.four_hour_csv),
        config,
    )
    payload = {
        "summary": result.summary.__dict__,
        "trades": [trade.__dict__ for trade in result.trades],
    }
    print(json.dumps(payload, indent=2, sort_keys=True, default=_decimal_default))


if __name__ == "__main__":
    main()
