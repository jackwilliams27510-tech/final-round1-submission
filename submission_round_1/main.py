#!/usr/bin/env python3
# Copied minimal runner of `main.py` into submission folder for standalone runs.
def parse_csv_line(row):
    time = int(row[0])
    product = row[-1]
    order_depth = {}
    for i in range(1, len(row) - 1, 2):
        price = int(row[i])
        qty = int(row[i + 1])
        order_depth[price] = qty
    return time, product, order_depth
import csv
import itertools
import numpy as np
import sys
import random
try:
    from pair_scan_cuths import build_mid_depth, run_pair_backtest
except Exception:
    build_mid_depth = None
    run_pair_backtest = None

PRODUCTS = [
    "CASTLE_STOCKS",
    "CUTHS_STOCKS",
    "HATFIELD_STOCKS",
    "COLLINGWOOD_STOCKS",
    "CHADS_STOCKS",
    "JOHNS_STOCKS",
]

def load_market_data(csv_path):
    market_data = {}
    row_count = 0
    with open(csv_path, newline='') as csvfile:
        reader = csv.reader(csvfile)
        header = next(reader, None)
        for row in reader:
            row_count += 1
            time, product, order_depth = parse_csv_line(row)
            if time not in market_data:
                market_data[time] = {}
            market_data[time][product] = order_depth
    print(f"[DIAG] Loaded {row_count} rows from CSV.")
    return market_data

if __name__ == "__main__":
    print('[DIAG] submission/main.py runner')
    csv_path = 'Round_1.csv'
    try:
        market_data = load_market_data(csv_path)
        print(f'[DIAG] CSV loaded successfully. {len(market_data)} time steps.')
    except Exception as e:
        print(f'[DIAG] Failed to load CSV: {e}')
        import sys; sys.exit(1)

    # simple smoke: run pair runner if present
    if len(sys.argv) > 1 and sys.argv[1] == 'run_pair_demo':
        params_path = 'best_pair_params_CUTHS_CASTLE_STOCKS_382_20251120_000651.json'
        import json
        with open(params_path, 'r') as f:
            params = json.load(f)
        params['pair_hedge'] = True
        # choose a partner
        partner = 'CASTLE_STOCKS'
        if run_pair_backtest is not None:
            times, mid_map, depth_map = build_mid_depth(market_data, PRODUCTS)
            cash, log = run_pair_backtest(market_data, times, mid_map, depth_map, params, 'CUTHS_STOCKS', partner)
            print(f"[RESULT] P&L={cash:.2f}, trades={len(log)}")
        else:
            print('[DIAG] run_pair_backtest not available in this copy.')
