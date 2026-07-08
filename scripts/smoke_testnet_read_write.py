from __future__ import annotations

import argparse
import json
from decimal import Decimal

from dual_sleeve_trader.config.runtime import load_runtime_config
from dual_sleeve_trader.core.enums import OrderSide
from dual_sleeve_trader.ops.testnet_read_write_smoke import (
    TestnetSmokeOrderConfig,
    result_to_dict,
    run_testnet_read_write_smoke,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run gated Binance testnet read/write smoke test.")
    parser.add_argument("--env-file", default=None)
    parser.add_argument("--symbol", default=None)
    parser.add_argument("--side", choices=[OrderSide.BUY.value, OrderSide.SELL.value], default=OrderSide.BUY.value)
    parser.add_argument("--quantity", required=True)
    parser.add_argument("--limit-price", required=True)
    parser.add_argument("--non-marketable-margin", default="0.2")
    parser.add_argument("--allow-marketable-test-order", action="store_true")
    parser.add_argument("--i-understand-this-places-testnet-order", action="store_true")
    args = parser.parse_args()

    runtime = load_runtime_config(args.env_file)
    order_config = TestnetSmokeOrderConfig(
        symbol=args.symbol or runtime.smoke_symbol,
        side=OrderSide(args.side),
        quantity=Decimal(args.quantity),
        limit_price=Decimal(args.limit_price),
        non_marketable_margin=Decimal(args.non_marketable_margin),
        require_non_marketable=not args.allow_marketable_test_order,
    )
    result = run_testnet_read_write_smoke(
        runtime,
        order_config,
        acknowledge_testnet_order=args.i_understand_this_places_testnet_order,
    )
    print(json.dumps(result_to_dict(result), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
