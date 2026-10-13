"""Inventory Policy Simulation & Backtesting Engine (Module 2).

Deterministic day-by-day backtest of five classical replenishment policies
(min_Q, base_stock, min_max, periodic_review, hybrid) over each product's
REAL daily demand series from ``sales_history``. Every result is computed
from database rows; nothing is invented. Values that cannot be computed
are returned as ``None`` and products that cannot be simulated are listed
under ``skipped`` with the reason.

Only business settings that no table contains are module-level constants,
and they are echoed back in the response under ``settings``.
"""

import math
from datetime import timedelta
from typing import Dict, Any, List, Optional, Tuple

import numpy as np
from scipy.stats import norm
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.app.core.database import SessionLocal
from backend.app.models.models import Product, SalesHistory


# --------------------------------------------------------------------------
# Business settings (not stored in any table) -- reported under "settings".
# --------------------------------------------------------------------------
TOP_N_PRODUCTS = 20             # products simulated (ranked by units sold)
MIN_HISTORY_DAYS = 28           # min calendar span of sales history per product
LOOKBACK_DAYS = 180             # most recent days of each product's history used
TARGET_SERVICE_LEVEL = 0.95     # cycle service level target -> z-score
TARGET_FILL_RATE_PCT = 95.0     # min avg fill rate for a policy to be "qualifying"
HOLDING_RATE_PER_YEAR = 0.20    # annual holding cost as fraction of unit cost
ORDER_COST = 50.0               # fixed cost per replenishment order (currency)
REVIEW_PERIOD_DAYS = 7          # R for periodic_review and hybrid policies

POLICIES = ["min_Q", "base_stock", "min_max", "periodic_review", "hybrid"]
BASELINE_POLICY = "base_stock"

POLICY_LABELS = {
    "min_Q": "Min-Q (s, Q)",
    "base_stock": "Base Stock (S-1, S)",
    "min_max": "Min-Max (s, S)",
    "periodic_review": "Periodic Review (R, S)",
    "hybrid": "Hybrid (R, s, S)",
}

POLICY_DESCRIPTIONS = {
    "min_Q": "Continuous review (s, Q): when inventory position <= s, order enough multiples of Q (EOQ) to lift it above s.",
    "base_stock": "Daily review one-for-one (S-1, S): every day, order up to base-stock level S_b = mean*(L+1) + z*std*sqrt(L+1).",
    "min_max": "Continuous review (s, S): when inventory position <= s, order up to S = s + EOQ.",
    "periodic_review": f"Periodic review (R, S): every {REVIEW_PERIOD_DAYS} days order up to T = mean*(R+L) + z*std*sqrt(R+L).",
    "hybrid": f"Periodic (R, s, S): every {REVIEW_PERIOD_DAYS} days, if inventory position <= T order up to T + EOQ.",
}

POLICY_SUITABILITY = {
    "min_Q": "Fixed lot sizes (EOQ / supplier pack quantities) with continuous stock visibility",
    "base_stock": "Low ordering cost, fast-moving items where daily replenishment is feasible",
    "min_max": "Continuous visibility with variable order quantities",
    "periodic_review": "Scheduled ordering cycles / consolidated supplier deliveries",
    "hybrid": "Scheduled reviews that skip orders when stock is still sufficient",
}


def _r(value: Optional[float], nd: int = 2) -> Optional[float]:
    if value is None:
        return None
    try:
        if math.isnan(value) or math.isinf(value):
            return None
    except TypeError:
        return None
    return round(float(value), nd)


def _mean(values: List[float]) -> Optional[float]:
    return float(np.mean(values)) if values else None


class InventoryPolicySimulationEngine:
    """Enterprise Policy Simulation & Review Backtest Engine."""

    def __init__(self, db: Optional[Session] = None):
        self.db = db

    def _get_db(self) -> Session:
        return self.db if self.db is not None else SessionLocal()

    # ------------------------------------------------------------------
    # Settings / traces
    # ------------------------------------------------------------------
    @staticmethod
    def _settings() -> Dict[str, Any]:
        return {
            "top_n_products": TOP_N_PRODUCTS,
            "min_history_days": MIN_HISTORY_DAYS,
            "lookback_days": LOOKBACK_DAYS,
            "target_service_level": TARGET_SERVICE_LEVEL,
            "z_score": _r(float(norm.ppf(TARGET_SERVICE_LEVEL)), 4),
            "target_fill_rate_pct": TARGET_FILL_RATE_PCT,
            "holding_rate_per_year": HOLDING_RATE_PER_YEAR,
            "order_cost": ORDER_COST,
            "review_period_days": REVIEW_PERIOD_DAYS,
            "baseline_policy_for_capital_efficiency": BASELINE_POLICY,
            "note": "Business settings not stored in any database table; all other inputs come from products and sales_history.",
        }

    @staticmethod
    def _cost_traces() -> Dict[str, str]:
        return {
            "fill_rate_formula": "Fill Rate = (Units Filled / Units Demanded) * 100% (lost-sales model)",
            "cycle_service_level_formula": "Cycle Service Level = Days With No Stockout / Simulated Days * 100%",
            "holding_cost_formula": (
                f"Holding Cost = Avg On-Hand Units * products.unit_cost * {HOLDING_RATE_PER_YEAR:.0%} "
                f"annual holding rate * Simulated Days / 365"
            ),
            "ordering_cost_formula": f"Ordering Cost = Orders Placed * {ORDER_COST:.2f} fixed cost per order",
            "total_cost_formula": "Total Cost = Holding Cost + Ordering Cost",
        }

    def _global_trace(self) -> Dict[str, str]:
        z = float(norm.ppf(TARGET_SERVICE_LEVEL))
        return {
            "methodology": (
                "Deterministic day-by-day historical backtest (single run per SKU x policy) over each "
                "product's real daily demand series; lost-sales model; orders arrive after "
                "products.lead_time_days; starting on-hand = the policy's order-up-to level."
            ),
            "demand_series": (
                f"Daily units = SUM(sales_history.quantity_sold) per calendar day, missing days = 0, "
                f"last {LOOKBACK_DAYS} days of each product's history; products need >= {MIN_HISTORY_DAYS} "
                f"days of history; top {TOP_N_PRODUCTS} by units sold."
            ),
            "parameter_equations": (
                f"z = norm.ppf({TARGET_SERVICE_LEVEL}) = {z:.4f}; SS = z * std_daily * sqrt(L); "
                f"s = mean_daily * L + SS; EOQ = sqrt(2 * mean_daily*365 * {ORDER_COST:.2f} / "
                f"({HOLDING_RATE_PER_YEAR} * unit_cost)); S = s + EOQ; "
                f"S_b = mean*(L+1) + z*std*sqrt(L+1); T = mean*(R+L) + z*std*sqrt(R+L) with R = {REVIEW_PERIOD_DAYS}"
            ),
            "fill_rate_equation": "Fill Rate = (Units Filled / Units Demanded) * 100%",
            "holding_cost_equation": (
                f"Holding Cost = Avg On-Hand Units * Unit Cost * {HOLDING_RATE_PER_YEAR:.0%} * Days / 365"
            ),
            "ordering_cost_equation": f"Ordering Cost = Orders Placed * {ORDER_COST:.2f}",
            "best_policy_rule": (
                f"Lowest average total cost among policies with average fill rate >= {TARGET_FILL_RATE_PCT}%; "
                f"if none qualify, the highest average fill rate."
            ),
            "capital_efficiency_equation": (
                f"(Sum avg inventory value under {BASELINE_POLICY} - under best policy) / "
                f"under {BASELINE_POLICY} * 100%; inventory value = avg on-hand units * unit_cost"
            ),
            "data_source_tables": "products (unit_cost, lead_time_days), sales_history (date, quantity_sold)",
            "explanation": "All figures are computed from database rows; uncomputable values are null.",
        }

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------
    def _load_candidates(self, db: Session) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        ranked = (
            db.query(
                SalesHistory.product_id,
                func.sum(SalesHistory.quantity_sold).label("units"),
            )
            .group_by(SalesHistory.product_id)
            .order_by(func.sum(SalesHistory.quantity_sold).desc())
            .all()
        )
        candidates: List[Dict[str, Any]] = []
        skipped: List[Dict[str, Any]] = []
        if not ranked:
            return candidates, skipped

        product_ids = [r[0] for r in ranked if r[0] is not None]
        products = {p.id: p for p in db.query(Product).filter(Product.id.in_(product_ids)).all()}

        for pid, units in ranked:
            if len(candidates) >= TOP_N_PRODUCTS:
                break
            if pid is None or units is None or float(units) <= 0:
                continue
            p = products.get(pid)
            if p is None:
                skipped.append({"product_id": pid, "sku": None, "sku_name": None,
                                "reason": "product_id in sales_history has no row in products"})
                continue
            base = {"product_id": pid, "sku": p.sku, "sku_name": p.name}
            if not p.lead_time_days or int(p.lead_time_days) <= 0:
                skipped.append({**base, "reason": "products.lead_time_days is null or 0"})
                continue
            if not p.unit_cost or float(p.unit_cost) <= 0:
                skipped.append({**base, "reason": "products.unit_cost is null or 0 (EOQ/holding cost not computable)"})
                continue

            rows = (
                db.query(SalesHistory.date, SalesHistory.quantity_sold)
                .filter(SalesHistory.product_id == pid)
                .all()
            )
            daily: Dict[Any, float] = {}
            for d, q in rows:
                if d is None or q is None:
                    continue
                key = d.date() if hasattr(d, "date") else d
                daily[key] = daily.get(key, 0.0) + float(q)
            if not daily:
                skipped.append({**base, "reason": "no dated sales_history rows"})
                continue

            last_day = max(daily)
            first_day = max(min(daily), last_day - timedelta(days=LOOKBACK_DAYS - 1))
            span = (last_day - first_day).days + 1
            if span < MIN_HISTORY_DAYS:
                skipped.append({**base, "reason": f"only {span} days of sales history (< {MIN_HISTORY_DAYS} required)"})
                continue
            series = np.array(
                [daily.get(first_day + timedelta(days=i), 0.0) for i in range(span)], dtype=float
            )
            candidates.append({
                **base,
                "unit_cost": float(p.unit_cost),
                "lead_time": int(p.lead_time_days),
                "demand": series,
                "period_start": first_day.isoformat(),
                "period_end": last_day.isoformat(),
            })
        return candidates, skipped

    # ------------------------------------------------------------------
    # Simulation
    # ------------------------------------------------------------------
    @staticmethod
    def _parameters(mean_d: float, std_d: float, L: int, unit_cost: float) -> Dict[str, float]:
        z = float(norm.ppf(TARGET_SERVICE_LEVEL))
        R = REVIEW_PERIOD_DAYS
        ss = z * std_d * math.sqrt(L)
        s = mean_d * L + ss
        annual_demand = mean_d * 365.0
        eoq = math.sqrt(2.0 * annual_demand * ORDER_COST / (HOLDING_RATE_PER_YEAR * unit_cost))
        q = max(1.0, math.ceil(eoq))
        s_int = math.ceil(s)
        S = s_int + q
        S_b = math.ceil(mean_d * (L + 1) + z * std_d * math.sqrt(L + 1))
        T = math.ceil(mean_d * (R + L) + z * std_d * math.sqrt(R + L))
        return {"z": z, "safety_stock": ss, "s": s_int, "eoq": eoq, "Q": q, "S": S,
                "S_b": S_b, "T": T, "T_plus_Q": T + q}

    @staticmethod
    def _simulate(policy: str, demand: np.ndarray, L: int, prm: Dict[str, float]) -> Dict[str, float]:
        days = len(demand)
        R = REVIEW_PERIOD_DAYS
        s, Q, S = prm["s"], prm["Q"], prm["S"]
        S_b, T, TQ = prm["S_b"], prm["T"], prm["T_plus_Q"]
        start = {"min_Q": s + Q, "base_stock": S_b, "min_max": S,
                 "periodic_review": T, "hybrid": TQ}[policy]

        arrivals = np.zeros(days + L + 1)
        on_hand = float(start)
        on_order = 0.0
        filled_total = 0.0
        stockout_days = 0
        orders = 0
        end_stock = np.empty(days)

        for t in range(days):
            arr = arrivals[t]
            if arr:
                on_hand += arr
                on_order -= arr
            d = demand[t]
            f = d if on_hand >= d else on_hand
            if f < d:
                stockout_days += 1
            on_hand -= f
            filled_total += f
            end_stock[t] = on_hand

            ip = on_hand + on_order
            qty = 0.0
            if policy == "min_Q":
                if ip <= s:
                    qty = Q * (math.floor((s - ip) / Q) + 1)
            elif policy == "base_stock":
                if ip < S_b:
                    qty = S_b - ip
            elif policy == "min_max":
                if ip <= s:
                    qty = S - ip
            elif policy == "periodic_review":
                if t % R == 0 and ip < T:
                    qty = T - ip
            elif policy == "hybrid":
                if t % R == 0 and ip <= T:
                    qty = TQ - ip
            if qty > 0:
                orders += 1
                on_order += qty
                arrivals[t + L] += qty

        demanded = float(demand.sum())
        return {
            "starting_stock": float(start),
            "demanded": demanded,
            "filled": filled_total,
            "lost": demanded - filled_total,
            "fill_rate_pct": (filled_total / demanded * 100.0) if demanded > 0 else None,
            "csl_pct": (days - stockout_days) / days * 100.0,
            "avg_inv": float(end_stock.mean()),
            "orders": orders,
            "days": days,
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def get_policy_simulation_intelligence(self) -> Dict[str, Any]:
        """Backtests replenishment policies over real database demand history."""
        db = self._get_db()
        should_close = (self.db is None)
        try:
            candidates, skipped = self._load_candidates(db)
            if not candidates:
                return self._empty_response(db, skipped)

            runs: List[Dict[str, Any]] = []
            sku_policies: List[Tuple[Dict[str, Any], List[Dict[str, Any]]]] = []
            agg = {p: {"fill": [], "csl": [], "inv": [], "inv_value": [], "hold": [], "ord": [], "total": []}
                   for p in POLICIES}

            for c in candidates:
                demand = c["demand"]
                mean_d = float(demand.mean())
                std_d = float(demand.std(ddof=1)) if len(demand) > 1 else 0.0
                L, uc = c["lead_time"], c["unit_cost"]
                prm = self._parameters(mean_d, std_d, L, uc)
                sku_runs = []
                for pol in POLICIES:
                    res = self._simulate(pol, demand, L, prm)
                    holding = res["avg_inv"] * uc * HOLDING_RATE_PER_YEAR * res["days"] / 365.0
                    ordering = res["orders"] * ORDER_COST
                    total = holding + ordering
                    order_qty_or_max = {"min_Q": prm["Q"], "base_stock": prm["S_b"], "min_max": prm["S"],
                                        "periodic_review": prm["T"], "hybrid": prm["T_plus_Q"]}[pol]
                    rop_used = {"min_Q": prm["s"], "base_stock": None, "min_max": prm["s"],
                                "periodic_review": None, "hybrid": prm["T"]}[pol]
                    entry = {
                        "product_id": c["product_id"],
                        "sku": c["sku"],
                        "sku_name": c["sku_name"],
                        "policy": pol,
                        "target_service_level_pct": _r(TARGET_SERVICE_LEVEL * 100, 1),
                        "reorder_point_used": rop_used,
                        "order_qty_or_max": order_qty_or_max,
                        "item_fill_rate_pct": _r(res["fill_rate_pct"], 1),
                        "cycle_service_level_pct": _r(res["csl_pct"], 1),
                        "average_inventory_units": _r(res["avg_inv"], 1),
                        "safety_stock_units": _r(prm["safety_stock"], 1),
                        "holding_cost": _r(holding, 2),
                        "ordering_cost": _r(ordering, 2),
                        "total_logistics_cost": _r(total, 2),
                        "lost_sales_units": _r(res["lost"], 1),
                        "orders_placed": res["orders"],
                        "starting_stock_units": res["starting_stock"],
                        "simulated_days": res["days"],
                        "period_start": c["period_start"],
                        "period_end": c["period_end"],
                        "lead_time_days": L,
                        "unit_cost": uc,
                        "mean_daily_demand": _r(mean_d, 3),
                        "std_daily_demand": _r(std_d, 3),
                        "eoq_units": _r(prm["eoq"], 1),
                    }
                    runs.append(entry)
                    sku_runs.append(entry)
                    a = agg[pol]
                    if res["fill_rate_pct"] is not None:
                        a["fill"].append(res["fill_rate_pct"])
                    a["csl"].append(res["csl_pct"])
                    a["inv"].append(res["avg_inv"])
                    a["inv_value"].append(res["avg_inv"] * uc)
                    a["hold"].append(holding)
                    a["ord"].append(ordering)
                    a["total"].append(total)
                sku_policies.append((c, sku_runs))

            cost_traces = self._cost_traces()
            policy_comparison = []
            for pol in POLICIES:
                a = agg[pol]
                policy_comparison.append({
                    "policy": pol,
                    "policy_label": POLICY_LABELS[pol],
                    "avg_fill_rate_pct": _r(_mean(a["fill"]), 1),
                    "cycle_service_level_pct": _r(_mean(a["csl"]), 1),
                    "avg_inventory_level_units": _r(_mean(a["inv"]), 1),
                    "avg_inventory_value": _r(_mean(a["inv_value"]), 2),
                    "avg_holding_cost": _r(_mean(a["hold"]), 2),
                    "avg_ordering_cost": _r(_mean(a["ord"]), 2),
                    "avg_total_cost": _r(_mean(a["total"]), 2),
                    "skus_simulated": len(a["total"]),
                    "description": POLICY_DESCRIPTIONS[pol],
                    "suitability": POLICY_SUITABILITY[pol],
                    "calculation_trace": cost_traces,
                })

            # Best policy overall
            raw = {pol: {"fill": _mean(agg[pol]["fill"]), "total": _mean(agg[pol]["total"]),
                         "inv_value_sum": float(sum(agg[pol]["inv_value"]))} for pol in POLICIES}
            qualifying = [p for p in POLICIES if raw[p]["fill"] is not None and raw[p]["fill"] >= TARGET_FILL_RATE_PCT]
            best_rule_met = bool(qualifying)
            if qualifying:
                best_policy = min(qualifying, key=lambda p: raw[p]["total"])
            else:
                with_fill = [p for p in POLICIES if raw[p]["fill"] is not None]
                best_policy = max(with_fill, key=lambda p: raw[p]["fill"]) if with_fill else None

            capital_gain = None
            if best_policy is not None and raw[BASELINE_POLICY]["inv_value_sum"] > 0:
                base_v = raw[BASELINE_POLICY]["inv_value_sum"]
                capital_gain = (base_v - raw[best_policy]["inv_value_sum"]) / base_v * 100.0

            all_fill = [r["item_fill_rate_pct"] for r in runs if r["item_fill_rate_pct"] is not None]
            avg_sim_fill = _r(_mean(all_fill), 1)

            # Best policy per SKU
            sku_recommendations = []
            for c, pols in sku_policies:
                qual = [p for p in pols if p["item_fill_rate_pct"] is not None
                        and p["item_fill_rate_pct"] >= TARGET_FILL_RATE_PCT]
                if qual:
                    best = min(qual, key=lambda x: x["total_logistics_cost"])
                    rule = f"lowest total cost among policies with fill rate >= {TARGET_FILL_RATE_PCT}%"
                else:
                    with_fill = [p for p in pols if p["item_fill_rate_pct"] is not None]
                    if not with_fill:
                        continue
                    best = max(with_fill, key=lambda x: x["item_fill_rate_pct"])
                    rule = f"no policy reached {TARGET_FILL_RATE_PCT}% fill rate; highest fill rate chosen"
                base = next(p for p in pols if p["policy"] == "min_Q")
                days = best["simulated_days"]
                period_saving = base["total_logistics_cost"] - best["total_logistics_cost"]
                annual_saving = period_saving * 365.0 / days if days else None
                sku_recommendations.append({
                    "product_id": c["product_id"],
                    "sku": c["sku"],
                    "sku_name": c["sku_name"],
                    "recommended_policy": best["policy"],
                    "achieved_fill_rate": best["item_fill_rate_pct"],
                    "cycle_service_level_pct": best["cycle_service_level_pct"],
                    "avg_inventory": best["average_inventory_units"],
                    "annual_cost_savings": _r(annual_saving, 2),
                    "rationale": (
                        f"'{best['policy']}' selected ({rule}): fill rate {best['item_fill_rate_pct']}%, "
                        f"avg {best['average_inventory_units']} units on hand, total cost "
                        f"{best['total_logistics_cost']:.2f} over {days} days vs {base['total_logistics_cost']:.2f} "
                        f"for min_Q."
                    ),
                    "calculation_trace": {
                        "tested_policies": [p["policy"] for p in pols],
                        "selection_rule": rule,
                        "best_policy_cost": f"{best['total_logistics_cost']:.2f}",
                        "baseline_min_q_cost": f"{base['total_logistics_cost']:.2f}",
                        "simulated_period": f"{c['period_start']} to {c['period_end']} ({days} days)",
                        "formula": "Annual Cost Savings = (min_Q Total Cost - Selected Policy Total Cost) * 365 / Simulated Days",
                        "data_source_tables": "sales_history (daily demand series), products (lead_time_days, unit_cost)",
                    },
                })

            recommendations = self._build_recommendations(
                best_policy, best_rule_met, raw, capital_gain, agg, sku_recommendations)

            return {
                "module_name": "Inventory Optimization & Policy Simulation",
                "module_key": "policy_simulation",
                "database_info": {
                    "is_connected": True,
                    "source": self._source_label(db),
                    "skus_evaluated": len(candidates),
                    "simulation_runs": len(runs),
                    "fallback_used": False,
                },
                "calculation_trace": self._global_trace(),
                "settings": self._settings(),
                "summary": {
                    "total_simulation_runs": len(runs),
                    "skus_evaluated": len(candidates),
                    "policies_tested_count": len(POLICIES),
                    "top_performing_policy": best_policy,
                    "top_policy_meets_fill_target": best_rule_met,
                    "avg_simulated_fill_rate_pct": avg_sim_fill,
                    "capital_efficiency_gain_pct": _r(capital_gain, 1),
                    "capital_efficiency_baseline_policy": BASELINE_POLICY,
                    "skus_skipped": len(skipped),
                },
                "policy_comparison": policy_comparison,
                "sku_recommendations": sku_recommendations,
                "simulation_runs": runs,
                "recommendations": recommendations,
                "skipped": skipped,
            }
        finally:
            if should_close:
                db.close()

    # ------------------------------------------------------------------
    @staticmethod
    def _build_recommendations(best_policy, best_rule_met, raw, capital_gain, agg, sku_recs) -> List[Dict[str, Any]]:
        recs: List[Dict[str, Any]] = []
        if best_policy is None:
            return recs
        best_fill = raw[best_policy]["fill"]
        best_total = raw[best_policy]["total"]
        if best_rule_met:
            title = f"Adopt {POLICY_LABELS[best_policy]} as default replenishment policy"
            details = (
                f"Across {len(agg[best_policy]['total'])} backtested SKUs, {best_policy} had the lowest average "
                f"total cost ({best_total:.2f}) among policies averaging >= {TARGET_FILL_RATE_PCT}% fill rate, "
                f"achieving {best_fill:.1f}%."
            )
        else:
            title = f"No policy reached the {TARGET_FILL_RATE_PCT}% fill-rate target"
            details = (
                f"Best achievable average fill rate was {best_fill:.1f}% under {best_policy}; review lead times "
                f"or the service-level setting."
            )
        if capital_gain is not None and best_policy != BASELINE_POLICY:
            impact = (f"{-capital_gain:.1f}% higher average inventory value than {BASELINE_POLICY} "
                      f"(traded for fewer orders)") if capital_gain < 0 else \
                f"{capital_gain:.1f}% lower average inventory value vs {BASELINE_POLICY}"
        else:
            impact = f"Average fill rate {best_fill:.1f}%, average total cost {best_total:.2f} per SKU"
        recs.append({"title": title, "impact": impact, "details": details,
                     "urgency": "HIGH" if not best_rule_met else "MEDIUM"})

        # Ordering-cost vs holding-cost balance for the best policy
        hold = _mean(agg[best_policy]["hold"]) or 0.0
        ordc = _mean(agg[best_policy]["ord"]) or 0.0
        if hold + ordc > 0:
            share = ordc / (hold + ordc) * 100.0
            recs.append({
                "title": f"Cost mix under {best_policy}: ordering {share:.1f}% / holding {100 - share:.1f}%",
                "impact": f"Avg ordering cost {ordc:.2f} vs holding cost {hold:.2f} per SKU",
                "details": (
                    f"Computed with ORDER_COST={ORDER_COST:.2f} per order and HOLDING_RATE={HOLDING_RATE_PER_YEAR:.0%}/yr "
                    f"over the backtest period."
                ),
                "urgency": "LOW",
            })

        # SKUs below the fill target even under their best policy
        below = [s for s in sku_recs if s["achieved_fill_rate"] is not None
                 and s["achieved_fill_rate"] < TARGET_FILL_RATE_PCT]
        if below:
            names = ", ".join(str(s["sku"]) for s in below[:5])
            recs.append({
                "title": f"{len(below)} SKU(s) miss {TARGET_FILL_RATE_PCT}% fill rate under every policy",
                "impact": f"Lowest best-case fill rate {min(s['achieved_fill_rate'] for s in below):.1f}%",
                "details": f"Affected SKUs (first 5): {names}. Demand variability relative to lead time exceeds what the tested buffers cover.",
                "urgency": "HIGH",
            })

        # Distribution of recommended policies
        if sku_recs:
            counts: Dict[str, int] = {}
            for s in sku_recs:
                counts[s["recommended_policy"]] = counts.get(s["recommended_policy"], 0) + 1
            dist = ", ".join(f"{k}: {v}" for k, v in sorted(counts.items(), key=lambda kv: -kv[1]))
            total_savings = sum(s["annual_cost_savings"] for s in sku_recs if s["annual_cost_savings"] is not None)
            recs.append({
                "title": "Per-SKU policy assignment",
                "impact": f"Annualized cost change vs min_Q across SKUs: {total_savings:.2f}",
                "details": f"Recommended policy per SKU ({len(sku_recs)} SKUs) -> {dist}.",
                "urgency": "MEDIUM",
            })
        return recs

    @staticmethod
    def _source_label(db: Session) -> str:
        try:
            return f"Connected database ({db.get_bind().dialect.name})"
        except Exception:
            return "Connected database"

    def _empty_response(self, db: Optional[Session] = None, skipped: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        skipped = skipped or []
        return {
            "module_name": "Inventory Optimization & Policy Simulation",
            "module_key": "policy_simulation",
            "database_info": {
                "is_connected": True,
                "source": self._source_label(db) if db is not None else "Connected database",
                "skus_evaluated": 0,
                "simulation_runs": 0,
                "fallback_used": False,
            },
            "calculation_trace": self._global_trace(),
            "settings": self._settings(),
            "summary": {
                "total_simulation_runs": 0,
                "skus_evaluated": 0,
                "policies_tested_count": 0,
                "top_performing_policy": None,
                "top_policy_meets_fill_target": None,
                "avg_simulated_fill_rate_pct": None,
                "capital_efficiency_gain_pct": None,
                "capital_efficiency_baseline_policy": BASELINE_POLICY,
                "skus_skipped": len(skipped),
            },
            "policy_comparison": [],
            "sku_recommendations": [],
            "simulation_runs": [],
            "recommendations": [],
            "skipped": skipped,
        }
