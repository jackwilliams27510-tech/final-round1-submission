from datamodel import *

class Trader:
    def __init__(self):
        self.products = ["Call", "Put", "Underlying"]

        # Parity constants (from regression)
        self.parity_const = 10000
        self.parity_threshold = 3.9   # small tweak from original 4.0

        # Improved-quote MM sizes (kept identical to original)
        self.mm_size = 2
        self.mm_size_big = 4

        # Delta model (unchanged)
        self.delta_call = 0.46
        self.delta_put = -0.54

        # Hedging (unchanged)
        self.hedge_threshold = 5
        self.hedge_unit = 2

        # Inventory safety levels (kept identical)
        self.soft_limit = 35
        self.hard_limit = 48

        # For volatility calc
        self.last_under = None

    # ======================================================
    # Best bid/ask (correct extraction)
    # ======================================================
    def _best_prices(self, state, product):
        listing = Listing(state.orderbook[product], product)
        best_bid = max(listing.buy_orders.keys())
        best_ask = min(listing.sell_orders.keys())
        mid = (best_bid + best_ask) / 2
        return mid, best_bid, best_ask

    # ======================================================
    # Main strategy loop
    # ======================================================
    def run(self, state):
        orders = []
        pos = state.positions

        mids, bids, asks = {}, {}, {}
        for p in self.products:
            m, bb, ba = self._best_prices(state, p)
            mids[p] = m
            bids[p] = bb
            asks[p] = ba

        # ======================================================
        # Parity Arbitrage Only (original structure preserved)
        # ======================================================
        parity_error = mids["Call"] - mids["Put"] - mids["Underlying"] + self.parity_const
        arb_size = 1 if any(abs(pos[p]) > self.soft_limit for p in self.products) else 2

        if parity_error > self.parity_threshold:
            if (
                pos["Call"] - arb_size >= -self.hard_limit and
                pos["Put"]  + arb_size <= self.hard_limit and
                pos["Underlying"] + arb_size <= self.hard_limit
            ):
                orders.append(Order("Call", bids["Call"], -arb_size))
                orders.append(Order("Put",  asks["Put"], +arb_size))
                orders.append(Order("Underlying", asks["Underlying"], +arb_size))

        elif parity_error < -self.parity_threshold:
            if (
                pos["Call"] + arb_size <= self.hard_limit and
                pos["Put"]  - arb_size >= -self.hard_limit and
                pos["Underlying"] - arb_size >= -self.hard_limit
            ):
                orders.append(Order("Call", asks["Call"], +arb_size))
                orders.append(Order("Put",  bids["Put"], -arb_size))
                orders.append(Order("Underlying", bids["Underlying"], -arb_size))

        # ======================================================
        # Delta Hedging (unchanged original)
        # ======================================================
        call_inv = pos["Call"]
        put_inv = pos["Put"]
        under_inv = pos["Underlying"]

        option_delta = call_inv * self.delta_call + put_inv * self.delta_put
        net_delta = option_delta - under_inv

        if net_delta > self.hedge_threshold:
            hedge_size = min(self.hedge_unit, self.hard_limit - under_inv)
            orders.append(Order("Underlying", bids["Underlying"], -hedge_size))

        elif net_delta < -self.hedge_threshold:
            hedge_size = min(self.hedge_unit, self.hard_limit + under_inv)
            orders.append(Order("Underlying", asks["Underlying"], +hedge_size))

        return orders





