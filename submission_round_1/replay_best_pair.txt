import os
import sys
import json
import csv

# Ensure workspace root is on sys.path so imports work when running from
# the `submission_round_1` directory.
HERE = os.path.abspath(os.path.dirname(__file__))
WORKSPACE_ROOT = os.path.abspath(os.path.join(HERE, '..'))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

from main import load_market_data, PRODUCTS
from pair_scan_cuths import build_mid_depth, run_pair_backtest

CSV_PATH = "Round_1.csv"
PARAMS_PATH = "best_pair_params_CUTHS_CASTLE_STOCKS_382_20251120_000651.json"
OUT_LOG = "replay_best_pair_trade_log.csv"

def main():
    market_data = load_market_data(CSV_PATH)
    try:
        with open(PARAMS_PATH, 'r') as f:
            params = json.load(f)
    except Exception as e:
        print(f"[ERR] Failed to load params {PARAMS_PATH}: {e}")
        return

    # Build mids/depth maps the same way the pair-scan script does
    times, mid_map, depth_map = build_mid_depth(market_data, PRODUCTS)

    pnl, log = run_pair_backtest(market_data, times, mid_map, depth_map, params, 'CUTHS_STOCKS', 'CASTLE_STOCKS')
    print(f"[RESULT] Replayed pair CUTHS_STOCKS vs CASTLE_STOCKS: P&L={pnl:.2f}, trades={len(log)}")

    # Save trade log
    if log:
        with open(OUT_LOG, 'w', newline='') as f:
            w = csv.writer(f)
            w.writerow(['time', 'desc'])
            for t, desc in log:
                w.writerow([t, desc])
        print(f"[SAVED] Trade log saved to {OUT_LOG}")

if __name__ == '__main__':
    main()
