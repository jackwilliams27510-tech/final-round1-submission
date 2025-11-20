import json
import csv
import os
from datetime import datetime

# Local copy of the dedicated pair backtester for standalone submission.
# This file is copied from the workspace root and should run in the submission folder
# when `Round_1.csv` and the params JSON are present in the same folder.

CSV_PATH = "Round_1.csv"
PARAMS_PATH = "best_pair_params_CUTHS_CASTLE_STOCKS_382_20251120_000651.json"
OUT_SUMMARY = "pair_scan_cuths_summary.csv"


def load_params(path):
    with open(path, 'r') as f:
        return json.load(f)


def build_mid_depth(market_data, products):
    times = sorted(market_data.keys())
    mid_map = {t: {} for t in times}
    depth_map = {t: {} for t in times}
    for t in times:
        for p in products:
            if p in market_data[t]:
                prices = list(market_data[t][p].keys())
                if prices:
                    mid_map[t][p] = (max(prices) + min(prices)) / 2
                    depth_map[t][p] = sum(abs(q) for q in market_data[t][p].values())
                else:
                    mid_map[t][p] = None
                    depth_map[t][p] = 0
            else:
                mid_map[t][p] = None
                depth_map[t][p] = 0
    return times, mid_map, depth_map


def run_pair_backtest(market_data, times, mid_map, depth_map, base_params, leg_a, leg_b):
    params = dict(base_params)
    max_pos = 30
    position = {leg_a: 0, leg_b: 0}
    entry_price = {leg_a: None, leg_b: None}
    last_trade = {leg_a: -99999, leg_b: -99999}
    cash = 0.0
    trade_log = []

    initial_mid = {leg_a: None, leg_b: None}

    hist = {leg_a: [], leg_b: []}

    for i, t in enumerate(times):
        if mid_map[t].get(leg_a) is None or mid_map[t].get(leg_b) is None:
            if mid_map[t].get(leg_a) is not None and initial_mid[leg_a] is None:
                initial_mid[leg_a] = mid_map[t][leg_a]
            if mid_map[t].get(leg_b) is not None and initial_mid[leg_b] is None:
                initial_mid[leg_b] = mid_map[t][leg_b]
            continue

        mid_a = mid_map[t][leg_a]
        mid_b = mid_map[t][leg_b]
        if initial_mid[leg_a] is None:
            initial_mid[leg_a] = mid_a
        if initial_mid[leg_b] is None:
            initial_mid[leg_b] = mid_b

        hist[leg_a].append(mid_a)
        hist[leg_b].append(mid_b)
        lookback = int(params.get('lookback', 10))
        if len(hist[leg_a]) <= lookback:
            continue
        mid_past = hist[leg_a][-lookback-1]
        short_ret = (mid_a - mid_past) / (mid_past + 1e-9)

        full_ret = (mid_a - initial_mid[leg_a]) / (initial_mid[leg_a] + 1e-9)
        candidate_long = full_ret >= params.get('min_long_ret', 0.0)

        threshold = params.get('threshold', 0.005)
        cooldown = int(params.get('cooldown', 3))
        step = int(params.get('step', 1))

        # TP/SL checks per-leg
        for leg in (leg_a, leg_b):
            if position[leg] != 0 and entry_price[leg] is not None:
                if position[leg] > 0:
                    ret = (mid_map[t][leg] - entry_price[leg]) / (entry_price[leg] + 1e-9)
                else:
                    ret = (entry_price[leg] - mid_map[t][leg]) / (entry_price[leg] + 1e-9)
                if ret >= params.get('tp', 0.1) or ret <= -params.get('sl', 0.05):
                    if position[leg] > 0:
                        cash += position[leg] * mid_map[t][leg]
                        trade_log.append((t, f'EXIT SELL {position[leg]} {leg} @ {mid_map[t][leg]:.2f} (TP/SL)'))
                    else:
                        cash -= abs(position[leg]) * mid_map[t][leg]
                        trade_log.append((t, f'EXIT BUY {abs(position[leg])} {leg} @ {mid_map[t][leg]:.2f} (TP/SL)'))
                    position[leg] = 0
                    entry_price[leg] = None

        if i - last_trade[leg_a] < cooldown:
            continue

        if candidate_long and short_ret >= threshold:
            target_a = max_pos
            target_b = -max_pos
        elif (not candidate_long) and short_ret <= -threshold:
            target_a = -max_pos
            target_b = max_pos
        else:
            continue

        delta_a = target_a - position[leg_a]
        delta_b = target_b - position[leg_b]
        if delta_a == 0 and delta_b == 0:
            continue

        change_a = max(-step, min(step, delta_a))
        change_b = max(-step, min(step, delta_b))

        def exec_leg(leg, change_units, t):
            total_avail = depth_map[t].get(leg, 0)
            wanted = abs(change_units)
            filled = int(min(wanted, total_avail))
            if filled == 0:
                return 0, 0.0, 0.0
            prices_now = list(market_data[t][leg].keys())
            spread = (max(prices_now) - min(prices_now)) if prices_now else 0.0
            mid = mid_map[t][leg]
            ask = mid + spread / 2.0
            bid = mid - spread / 2.0
            if change_units > 0:
                exec_price = ask
                cash_delta = -filled * exec_price
            else:
                exec_price = bid
                cash_delta = filled * exec_price
            slippage_frac = params.get('slippage', 0.0)
            per_unit_fee = params.get('per_unit_fee', 0.0)
            fee_per_trade = params.get('fee_per_trade', 0.0)
            slippage_cost = filled * exec_price * slippage_frac
            unit_fees = filled * per_unit_fee
            cash_delta -= slippage_cost
            cash_delta -= (fee_per_trade + unit_fees)
            return filled if change_units > 0 else -filled, exec_price, cash_delta

        filled_a, price_a, cash_a = exec_leg(leg_a, change_a, t)
        filled_b, price_b, cash_b = exec_leg(leg_b, change_b, t)

        if filled_a != 0:
            position[leg_a] += filled_a
            cash += cash_a
            trade_log.append((t, f"{'BUY' if filled_a>0 else 'SELL'} {abs(filled_a)} {leg_a} @ {price_a:.2f} target={target_a} short_ret={short_ret:.4f}"))
            if entry_price[leg_a] is None:
                entry_price[leg_a] = price_a
            last_trade[leg_a] = i
        if filled_b != 0:
            position[leg_b] += filled_b
            cash += cash_b
            trade_log.append((t, f"{'BUY' if filled_b>0 else 'SELL'} {abs(filled_b)} {leg_b} @ {price_b:.2f} target={target_b} short_ret={short_ret:.4f}"))
            if entry_price[leg_b] is None:
                entry_price[leg_b] = price_b
            last_trade[leg_b] = i

    t_final = times[-1]
    for leg in (leg_a, leg_b):
        if leg in market_data[t_final]:
            prices = list(market_data[t_final][leg].keys())
            if not prices:
                continue
            mid = (max(prices) + min(prices)) / 2
            if position[leg] > 0:
                cash += position[leg] * mid
                trade_log.append((t_final, f'LIQUIDATE SELL {position[leg]} {leg} @ {mid:.2f}'))
            elif position[leg] < 0:
                cash -= abs(position[leg]) * mid
                trade_log.append((t_final, f'LIQUIDATE BUY {abs(position[leg])} {leg} @ {mid:.2f}'))
            position[leg] = 0

    return cash, trade_log


def main():
    # Attempt to load CSV and params from the same folder
    if not os.path.exists(CSV_PATH):
        print(f"[DIAG] Missing {CSV_PATH} in this folder. Place Round_1.csv here and retry.")
        return
    if not os.path.exists(PARAMS_PATH):
        print(f"[DIAG] Missing {PARAMS_PATH} in this folder. Place params JSON here and retry.")
        return

    # load market data lazily (simple CSV parser similar to main.py)
    market_data = {}
    with open(CSV_PATH, newline='') as csvfile:
        reader = csv.reader(csvfile)
        header = next(reader, None)
        for row in reader:
            time = int(row[0])
            product = row[-1]
            order_depth = {}
            for i in range(1, len(row) - 1, 2):
                price = int(row[i])
                qty = int(row[i + 1])
                order_depth[price] = qty
            if time not in market_data:
                market_data[time] = {}
            market_data[time][product] = order_depth

    params = load_params(PARAMS_PATH)
    # run only the CUTHS vs CASTLE pair as this is the canonical best
    times, mid_map, depth_map = build_mid_depth(market_data, ['CASTLE_STOCKS','CUTHS_STOCKS','HATFIELD_STOCKS','COLLINGWOOD_STOCKS','CHADS_STOCKS','JOHNS_STOCKS'])
    pnl, log = run_pair_backtest(market_data, times, mid_map, depth_map, params, 'CUTHS_STOCKS', 'CASTLE_STOCKS')
    print(f"[RESULT] CUTHS_STOCKS vs CASTLE_STOCKS P&L={pnl:.2f}, trades={len(log)}")


if __name__ == '__main__':
    main()
