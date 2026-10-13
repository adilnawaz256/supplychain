"""Recommendation Algorithm & Market Basket Analysis Engine (Module 4).

Mines transactional co-occurrence patterns (support, confidence, lift) from the
`orders` / `order_items` tables, builds cross-sell bundles from the strongest
rules with a measured basket-value uplift, and identifies bottom-octile slow
movers paired with their strongest real rule partner. Nothing is invented: values
that cannot be computed from the database are returned as None.
"""

from typing import Dict, Any, List, Optional
from collections import defaultdict

import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.app.core.database import SessionLocal
from backend.app.models.models import Product, Order, OrderItem, SalesHistory

# ---- Business settings (not stored in any table) -----------------------------
MIN_SUPPORT = 0.005
# Large, sparse basket sets (thousands of SKUs) rarely reach 0.5% support, so cap the
# required basket count; pairs seen in 10+ baskets are still a repeatable pattern.
MAX_MIN_PAIR_BASKETS = 10
MAX_RULES_RETURNED = 200
MIN_BASKETS_FOR_MINING = 5
MAX_BUNDLES = 6
SLOW_MOVER_PERCENTILE = 12.5   # bottom octile of units sold
MAX_SLOW_MOVERS_RETURNED = 50

PRIMARY_ALGORITHM = "Apriori / Frequent Itemset Association Rules (Lift > 1.0)"


def _settings() -> Dict[str, Any]:
    return {
        "min_support": MIN_SUPPORT,
        "max_min_pair_baskets": MAX_MIN_PAIR_BASKETS,
        "min_lift": 1.0,
        "max_rules_returned": MAX_RULES_RETURNED,
        "min_baskets_for_mining": MIN_BASKETS_FOR_MINING,
        "max_bundles": MAX_BUNDLES,
        "slow_mover_percentile": SLOW_MOVER_PERCENTILE,
        "max_slow_movers_returned": MAX_SLOW_MOVERS_RETURNED,
    }


class MarketBasketRecommendationEngine:
    """Enterprise Market Basket Cross-Sell & Inventory Liquidation Engine."""

    def __init__(self, db: Optional[Session] = None):
        self.db = db

    def _get_db(self) -> Session:
        return self.db if self.db is not None else SessionLocal()

    def get_market_basket_intelligence(self) -> Dict[str, Any]:
        """Association rules, cross-sell bundles and slow movers computed from live database records."""
        db = self._get_db()
        should_close = (self.db is None)

        try:
            products = db.query(Product.id, Product.name).all()
            if not products:
                return self._empty_response("No products in products table.")
            prod_map = {pid: name for pid, name in products}

            # 1. Baskets (single query) + per-order line value sums
            lines = db.query(OrderItem.order_id, OrderItem.product_id, OrderItem.total_price).all()
            baskets: Dict[int, set] = defaultdict(set)
            line_value: Dict[int, float] = defaultdict(float)
            for oid, pid, tp in lines:
                name = prod_map.get(pid)
                if name is not None:
                    baskets[oid].add(name)
                line_value[oid] += float(tp or 0.0)

            # Order value: orders.total_amount, else sum(order_items.total_price)
            order_value: Dict[int, Optional[float]] = {}
            if baskets:
                for oid, amt in db.query(Order.id, Order.total_amount).all():
                    if oid in baskets:
                        order_value[oid] = float(amt) if amt else (line_value.get(oid) or None)

            rules: List[Dict[str, Any]] = []
            item_counts: Dict[str, int] = defaultdict(int)
            pair_counts: Dict[tuple, int] = defaultdict(int)
            n_baskets = len(baskets)
            total_baskets = max(1, n_baskets)
            min_count = None

            if n_baskets >= MIN_BASKETS_FOR_MINING:
                for b_items in baskets.values():
                    for item in b_items:
                        item_counts[item] += 1
                    sorted_items = sorted(b_items)
                    for i in range(len(sorted_items)):
                        for j in range(i + 1, len(sorted_items)):
                            pair_counts[(sorted_items[i], sorted_items[j])] += 1

                min_count = min(max(3, int(MIN_SUPPORT * total_baskets)), MAX_MIN_PAIR_BASKETS)
                for (item_a, item_b), count in pair_counts.items():
                    if count < min_count:
                        continue
                    for ant, cons in ((item_a, item_b), (item_b, item_a)):
                        supp = count / total_baskets
                        conf_a_b = count / max(1, item_counts[ant])
                        supp_b = item_counts[cons] / total_baskets
                        lift = conf_a_b / max(1e-9, supp_b)
                        if lift <= 1.0:
                            continue
                        rules.append({
                            "rule_id": "",
                            "antecedent": ant,
                            "consequent": cons,
                            "support_pct": round(supp * 100, 2),
                            "confidence_pct": round(conf_a_b * 100, 1),
                            "lift": round(lift, 2),
                            "leverage": round(supp - ((item_counts[ant] / total_baskets) * supp_b), 4),
                            "strength": "VERY_STRONG" if lift > 10 else ("STRONG" if lift > 3 else "MODERATE"),
                            "suggested_action": f"Recommend '{cons}' at checkout whenever '{ant}' is added to cart.",
                            "calculation_trace": {
                                "support_formula": "Supp(A -> B) = Count(Baskets with A & B) / Total Baskets",
                                "confidence_formula": "Conf(A -> B) = Count(Baskets with A & B) / Count(Baskets with A)",
                                "lift_formula": "Lift = Conf(A -> B) / Supp(B)",
                                "support_value": f"{round(supp * 100, 2)}% ({count}/{total_baskets} baskets)",
                                "confidence_value": f"{round(conf_a_b * 100, 1)}% ({count}/{item_counts[ant]} baskets)",
                                "lift_value": f"{round(lift, 2)}x",
                                "min_support_baskets": min_count,
                                "data_source_tables": "orders, order_items, products",
                                "interpretation": f"Customers buying '{ant}' are {round(lift, 1)}x more likely to add '{cons}' than average cart baseline."
                            }
                        })

            rules.sort(key=lambda x: (x["lift"], x["confidence_pct"]), reverse=True)
            for i, r in enumerate(rules):
                r["rule_id"] = f"R-{i + 1:03d}"
            total_rules = len(rules)

            # 2. Cross-sell bundles with measured basket-value uplift
            top_rules = rules[:MAX_BUNDLES]
            needed = {r["antecedent"] for r in top_rules}
            baskets_with: Dict[str, List[int]] = defaultdict(list)
            if needed:
                for oid, items in baskets.items():
                    for it in needed & items:
                        baskets_with[it].append(oid)

            cross_sell_bundles = []
            for r in top_rules:
                a, b = r["antecedent"], r["consequent"]
                with_b, without_b = [], []
                for oid in baskets_with.get(a, []):
                    v = order_value.get(oid)
                    if v is None:
                        continue
                    (with_b if b in baskets[oid] else without_b).append(v)
                aov_ab = float(np.mean(with_b)) if with_b else None
                aov_a = float(np.mean(without_b)) if without_b else None
                uplift = round((aov_ab - aov_a) / aov_a * 100, 1) if (aov_ab is not None and aov_a) else None
                cross_sell_bundles.append({
                    "bundle_name": f"{a[:20]} + {b[:20]} Combo",
                    "primary_item": a,
                    "add_on_item": b,
                    "co_purchase_lift": r["lift"],
                    "conversion_probability_pct": r["confidence_pct"],
                    "discount_incentive": None,
                    "projected_atv_uplift_pct": uplift,
                    "calculation_trace": {
                        "atv_uplift_formula": "(AOV of baskets with A and B - AOV of baskets with A without B) / AOV(A without B) x 100",
                        "aov_with_both": round(aov_ab, 2) if aov_ab is not None else None,
                        "aov_primary_only": round(aov_a, 2) if aov_a is not None else None,
                        "baskets_with_both": len(with_b),
                        "baskets_primary_only": len(without_b),
                        "conversion_probability": "Rule confidence P(B | A)",
                        "order_value_source": "orders.total_amount (sum(order_items.total_price) when null/0)",
                    },
                })

            # 3. Slow movers: bottom octile of total units sold among products with sales
            sales_rows = (
                db.query(SalesHistory.product_id, func.sum(SalesHistory.quantity_sold))
                .group_by(SalesHistory.product_id)
                .all()
            )
            units_source = "sales_history.quantity_sold"
            if not sales_rows:
                sales_rows = (
                    db.query(OrderItem.product_id, func.sum(OrderItem.quantity))
                    .group_by(OrderItem.product_id)
                    .all()
                )
                units_source = "order_items.quantity"
            units = {pid: float(q or 0) for pid, q in sales_rows if pid in prod_map and q and q > 0}

            # strongest rule partner per product name (rules already sorted by lift desc)
            best_partner: Dict[str, Dict[str, Any]] = {}
            for r in rules:
                for me, other in ((r["antecedent"], r["consequent"]), (r["consequent"], r["antecedent"])):
                    if me not in best_partner:
                        best_partner[me] = {"partner": other, "lift": r["lift"], "rule_id": r["rule_id"]}

            slow_movers: List[Dict[str, Any]] = []
            octile_cutoff = None
            if units:
                vals = np.array(sorted(units.values()))
                octile_cutoff = float(np.percentile(vals, SLOW_MOVER_PERCENTILE))
                n_prod = len(vals)
                for pid, q in sorted(units.items(), key=lambda kv: kv[1]):
                    if q > octile_cutoff:
                        break
                    name = prod_map[pid]
                    pct_rank = round(float(np.searchsorted(vals, q, side="right")) / n_prod * 100, 1)
                    bp = best_partner.get(name)
                    slow_movers.append({
                        "sku_name": name,
                        "total_quantity_sold": int(q),
                        "velocity_tier": f"BOTTOM_OCTILE (P{pct_rank} of {n_prod} selling SKUs)",
                        "percentile_rank": pct_rank,
                        "liquidation_strategy": (
                            f"Pair with '{bp['partner']}' (strongest association, lift {bp['lift']}x, {bp['rule_id']})."
                            if bp else None
                        ),
                    })
            slow_count = len(slow_movers)

            avg_lift = round(float(np.mean([r["lift"] for r in rules])), 2) if rules else None
            avg_conf = round(float(np.mean([r["confidence_pct"] for r in rules])), 1) if rules else None

            # 4. Recommendations from computed numbers only
            recommendations = []
            uplifts = [b["projected_atv_uplift_pct"] for b in cross_sell_bundles if b["projected_atv_uplift_pct"] is not None]
            if cross_sell_bundles:
                top = cross_sell_bundles[0]
                impact = (f"Median observed basket-value uplift {round(float(np.median(uplifts)), 1)}% across {len(uplifts)} bundles"
                          if uplifts else f"{len(cross_sell_bundles)} bundles identified")
                recommendations.append({
                    "title": "Deploy Top Association Bundles at Checkout",
                    "impact": impact,
                    "details": f"Strongest rule: '{top['primary_item']}' -> '{top['add_on_item']}' with lift {top['co_purchase_lift']}x and confidence {top['conversion_probability_pct']}%.",
                    "urgency": "HIGH",
                })
            if slow_movers:
                paired = sum(1 for s in slow_movers if s["liquidation_strategy"])
                recommendations.append({
                    "title": "Liquidate Slow Movers via Associated Products",
                    "impact": f"{slow_count} bottom-octile SKUs (<= {round(octile_cutoff, 1)} units sold)",
                    "details": f"{paired} of {slow_count} slow movers have an association rule partner to bundle with.",
                    "urgency": "MEDIUM",
                })

            return {
                "module_name": "Recommendation Algorithm & Market Basket Cross-Sell",
                "module_key": "market_basket",
                "database_info": {
                    "is_connected": True,
                    "source": "Connected Database (orders, order_items, products, sales_history)",
                    "baskets_analyzed": n_baskets,
                    "rules_discovered": total_rules,
                    "fallback_used": False
                },
                "settings": _settings(),
                "calculation_trace": {
                    "methodology": "Apriori Association Rule Mining (Support, Confidence, Lift)",
                    "support_equation": "Support(A -> B) = Count(Transactions with A & B) / Total Transactions",
                    "confidence_equation": "Confidence(A -> B) = Count(Transactions with A & B) / Count(Transactions with A)",
                    "lift_equation": "Lift(A -> B) = Confidence(A -> B) / Support(B)",
                    "min_pair_baskets_applied": min_count,
                    "atv_uplift_equation": "(AOV baskets with A&B - AOV baskets with A only) / AOV(A only)",
                    "slow_mover_rule": f"Products with sales whose total units ({units_source}) <= P{SLOW_MOVER_PERCENTILE} = {round(octile_cutoff, 2) if octile_cutoff is not None else None}",
                    "data_source_tables": "orders, order_items, products, sales_history",
                    "explanation": (
                        f"Analyzed {n_baskets} baskets; {total_rules} rules with lift > 1.0 and at least {min_count} co-occurring baskets."
                        if min_count is not None else
                        f"Only {n_baskets} baskets; at least {MIN_BASKETS_FOR_MINING} required for rule mining."
                    ),
                },
                "summary": {
                    "total_rules_discovered": total_rules,
                    "avg_association_lift": avg_lift,
                    "avg_confidence_pct": avg_conf,
                    "slow_moving_skus_tracked": slow_count,
                    "active_bundle_opportunities": len(cross_sell_bundles),
                    "primary_algorithm": PRIMARY_ALGORITHM
                },
                "association_rules": rules[:MAX_RULES_RETURNED],
                "cross_sell_bundles": cross_sell_bundles,
                "slow_movers": slow_movers[:MAX_SLOW_MOVERS_RETURNED],
                "recommendations": recommendations,
            }
        finally:
            if should_close:
                db.close()

    def _empty_response(self, note: str = "") -> Dict[str, Any]:
        return {
            "module_name": "Recommendation Algorithm & Market Basket Cross-Sell",
            "module_key": "market_basket",
            "database_info": {
                "is_connected": True,
                "source": "Connected Database (orders, order_items, products, sales_history)",
                "baskets_analyzed": 0,
                "rules_discovered": 0,
                "fallback_used": False
            },
            "settings": _settings(),
            "calculation_trace": {"methodology": "Apriori Association Rule Mining (Support, Confidence, Lift)", "explanation": note},
            "summary": {
                "total_rules_discovered": 0,
                "avg_association_lift": None,
                "avg_confidence_pct": None,
                "slow_moving_skus_tracked": 0,
                "active_bundle_opportunities": 0,
                "primary_algorithm": PRIMARY_ALGORITHM
            },
            "association_rules": [],
            "cross_sell_bundles": [],
            "slow_movers": [],
            "recommendations": [],
        }
