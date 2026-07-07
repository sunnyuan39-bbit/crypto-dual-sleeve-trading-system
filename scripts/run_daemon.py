from __future__ import annotations

import argparse
import json

from dual_sleeve_trader.config.runtime import load_runtime_config
from dual_sleeve_trader.ops.daemon import DaemonConfig, build_daemon_runner, daemon_result_to_dict


def main() -> None:
    parser = argparse.ArgumentParser(description="Run local reconciliation daemon.")
    parser.add_argument("--env-file", default=None)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--interval-seconds", type=int, default=30)
    parser.add_argument("--max-iterations", type=int, default=None)
    parser.add_argument("--continue-on-mismatch", action="store_true")
    parser.add_argument("--refresh-positions", action="store_true")
    parser.add_argument("--require-real-testnet", action="store_true")
    args = parser.parse_args()

    runtime = load_runtime_config(args.env_file)
    max_iterations = 1 if args.once else args.max_iterations
    daemon_config = DaemonConfig(
        interval_seconds=args.interval_seconds,
        max_iterations=max_iterations,
        stop_on_mismatch=not args.continue_on_mismatch,
        refresh_positions_before_reconcile=args.refresh_positions,
    )
    runner = build_daemon_runner(
        runtime,
        daemon_config,
        allow_inert_fallback=not args.require_real_testnet,
    )
    results = runner.run()
    print(json.dumps([daemon_result_to_dict(result) for result in results], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
