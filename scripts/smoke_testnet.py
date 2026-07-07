from __future__ import annotations

import argparse
import json

from dual_sleeve_trader.config.runtime import load_runtime_config
from dual_sleeve_trader.ops.smoke import run_testnet_smoke


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a safe Binance testnet smoke check.")
    parser.add_argument("--env-file", default=None)
    parser.add_argument("--require-real-testnet", action="store_true")
    args = parser.parse_args()

    config = load_runtime_config(args.env_file)
    result = run_testnet_smoke(config, require_real_testnet=args.require_real_testnet)
    print(json.dumps(result.__dict__, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
