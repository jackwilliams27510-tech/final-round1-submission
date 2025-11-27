from datamodel import *

class Trader:
    def __init__(self):
        self.products = ["bond1","bond2","bond3","bond4","ETF1"]

        # tight & aggressive threshold
        self.threshold_etf1 = 1.25

        # base size (dynamic scaling overrides this)
        self.trade_size = 2


    # -------------------------------
    # MID / BID / ASK HELPER
    # -------------------------------
    def _mid_bid_ask(self, state, product):
        listings = Listing(state.orderbook[product], product)
        best_bid = next(iter(listings.buy_orders.keys()))
        best_ask = next(iter(listings.sell_orders.keys()))
        mid = (best_bid + best_ask) / 2
        return mid, best_bid, best_ask


    # -------------------------------
    # MAIN STRATEGY
    # -------------------------------
    def run(self, state):

        orders = []
        mids = {}
        best_bid = {}
        best_ask = {}

        # -------- Gather price data --------
        for p in self.products:
            mid, bid, ask = self._mid_bid_ask(state, p)
            mids[p] = mid
            best_bid[p] = bid
            best_ask[p] = ask

        # -------- Theoretical ETF1 value --------
        fair_etf1 = mids["bond1"] + mids["bond2"] + mids["bond3"]
        diff1 = mids["ETF1"] - fair_etf1

        # -------- Spread costs --------
        spread_etf = best_ask["ETF1"] - best_bid["ETF1"]
        spread_b1 = best_ask["bond1"] - best_bid["bond1"]
        spread_b2 = best_ask["bond2"] - best_bid["bond2"]
        spread_b3 = best_ask["bond3"] - best_bid["bond3"]
        avg_bond_spread = (spread_b1 + spread_b2 + spread_b3) / 3
        # -------- Effective mispricing --------
        effective_diff = diff1 - (spread_etf * 0.7)

        # -------- Volatility confirmation boost --------
        # If bonds move tightly together → price shock → arb tends to be reliable
        vol_boost = 1.0
        if abs(mids["bond1"] - mids["bond2"]) < 1.2 and abs(mids["bond2"] - mids["bond3"]) < 1.2:
            vol_boost = 1.28   # strong improvement without adding noise

        # -------- Trade quality score --------
        trade_quality = (effective_diff / max(spread_etf + 0.5, 1)) * vol_boost
        entry_margin = 0.05
        positions = state.positions
        limits = state.pos_limit

        def can_trade(prod, delta):
            return abs(positions[prod] + delta) <= limits[prod]


        # ================================================
        #   PACKAGE-C: AGGRESSIVE ETf1 DYNAMIC SIZING
        # ================================================
        raw_size = abs(trade_quality) ** 1.07 * 3.7   # stronger punch than your 5233 version
        size = max(1, min(int(raw_size), 11))

        # reduce size near ETF1 limits
        if abs(positions["ETF1"]) > 32:
            size = max(1, size // 2)

        # reduce size near bond limits
        if any(abs(positions[b]) > 28 for b in ["bond1","bond2","bond3"]):
            size = max(1, size // 2)


        # ================================================
        #   ETF1 OVERPRICED → SELL ETF1 & BUY BONDS
        # ================================================
   
        if trade_quality > self.threshold_etf1 + entry_margin:
            if can_trade("ETF1", -size) and all(can_trade(b, +size) for b in ["bond1","bond2","bond3"]):
                orders.append(Order("ETF1", best_bid["ETF1"], -size))
                for b in ["bond1","bond2","bond3"]:
                    orders.append(Order(b, best_ask[b], +size))


        # ================================================
        #   ETF1 UNDERPRICED → BUY ETF1 & SELL BONDS
        # ================================================
        if trade_quality < -self.threshold_etf1 - entry_margin:
            if can_trade("ETF1", +size) and all(can_trade(b, -size) for b in ["bond1","bond2","bond3"]):
                orders.append(Order("ETF1", best_ask["ETF1"], +size))
                for b in ["bond1","bond2","bond3"]:
                    orders.append(Order(b, best_bid[b], -size))



        # ================================================
        #   INVENTORY MANAGEMENT (SAFE & PROFITABLE)
        # ================================================
        for b in ["bond1","bond2","bond3"]:

            bond_spread = best_ask[b] - best_bid[b]

            # Only unwind when:
            # - position is large AND
            # - bond spreads are cheap AND
            # - trade_quality low (signal weaker)
            if positions[b] > 28 and bond_spread <= 3 and abs(trade_quality) < 0.8:
                if can_trade(b, -3):
                    orders.append(Order(b, best_bid[b], -3))

            if positions[b] < -30 and bond_spread <= 3 and abs(trade_quality) < 0.8:
                if can_trade(b, +2):
                    orders.append(Order(b, best_ask[b], +2))

        return orders

