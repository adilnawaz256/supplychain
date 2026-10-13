"""Pricing Optimization and Advanced Analytics Engine (Module 1).

Everything in this module is computed from the `products` and `sales_history`
tables. Nothing is invented: when a number cannot be computed from the data it
is returned as ``None`` (null) and the reason is stated.

Methods
-------
1. Demand-pattern classification (Syntetos-Boylan-Croston) on each product's
   daily demand series (calendar days between first and last sale, missing days
   filled with 0). ADI = days in span / days with demand; CV^2 = (std/mean)^2 of
   the non-zero daily demand sizes.
2. ABC product mix on revenue share and quantity share (A = top 80% cumulative,
   B = next 15%, C = rest).
3. Price elasticity from real price variation: log(qty) = a + b*log(price) fitted
   by least squares on daily (qty-weighted average price, total qty) points;
   elasticity = -b. Profit-optimal price P* = cost * e / (e - 1) when e > 1.
4. Single-period (newsvendor) ordering with normally distributed horizon demand
   estimated from the real daily demand series.

Business settings that no table contains are module-level constants below and
are reported in the output under ``settings``.
"""

from typing import Dict, Any, List, Optional
import math

import numpy as np
import pandas as pd
from scipy.stats import norm
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.app.core.database import SessionLocal
from backend.app.models.models import Product, SalesHistory


# ---------------------------------------------------------------------------
# Named business settings (not stored in any table). Reported under `settings`.
# ---------------------------------------------------------------------------
SBC_ADI_THRESHOLD = 1.32          # Syntetos-Boylan-Croston ADI cut-off
SBC_CV2_THRESHOLD = 0.49          # Syntetos-Boylan-Croston CV^2 cut-off
ABC_A_CUTOFF = 0.80               # cumulative share for class A
ABC_B_CUTOFF = 0.95               # cumulative share for class B (A + next 15%)
MIN_PRICE_POINTS = 4              # distinct prices (rounded to cents) needed for an elasticity fit
MIN_PERIODS_WITH_SALES = 8        # daily periods with sales needed for an elasticity fit
MAX_PRICE_CHANGE_PCT = 30.0       # recommended price change is clamped to +/- this %
SALVAGE_FRACTION = 0.40           # newsvendor salvage value as a fraction of unit cost
NEWSVENDOR_HORIZON_DAYS = 30      # newsvendor selling season length in days
DETAIL_LIST_LIMIT = 50            # max items in detailed per-product lists (top by revenue)

_COLORS = {"smooth": "#10b981", "intermittent": "#3b82f6", "erratic": "#f59e0b", "lumpy": "#ef4444"}
_DESCS = {
    "smooth": "Regular daily demand, fits standard ROP math",
    "intermittent": "Infrequent orders of steady quantities (Croston/TSB)",
    "erratic": "Frequent orders with highly variable sizes",
    "lumpy": "Spiky, sparse sales; requires buffer stock or Newsvendor",
}


def _settings() -> Dict[str, Any]:
    return {
        "sbc_adi_threshold": SBC_ADI_THRESHOLD,
        "sbc_cv2_threshold": SBC_CV2_THRESHOLD,
        "abc_a_cumulative_share": ABC_A_CUTOFF,
        "abc_b_cumulative_share": ABC_B_CUTOFF,
        "min_price_points_for_elasticity": MIN_PRICE_POINTS,
        "min_periods_with_sales_for_elasticity": MIN_PERIODS_WITH_SALES,
        "max_price_change_pct": MAX_PRICE_CHANGE_PCT,
        "newsvendor_salvage_fraction_of_cost": SALVAGE_FRACTION,
        "newsvendor_horizon_days": NEWSVENDOR_HORIZON_DAYS,
        "detail_list_limit": DETAIL_LIST_LIMIT,
    }


def _r(x: Optional[float], nd: int = 2) -> Optional[float]:
    if x is None:
        return None
    try:
        xf = float(x)
    except (TypeError, ValueError):
        return None
    if math.isnan(xf) or math.isinf(xf):
        return None
    return round(xf, nd)


def _abc(values: pd.Series) -> pd.Series:
    """ABC class per index from a non-negative value series."""
    total = float(values.sum())
    if total <= 0:
        return pd.Series([None] * len(values), index=values.index, dtype=object)
    s = values.sort_values(ascending=False)
    cum_before = (s.cumsum() - s) / total  # share accumulated before this item
    cls = pd.Series(np.where(cum_before < ABC_A_CUTOFF, "A",
                             np.where(cum_before < ABC_B_CUTOFF, "B", "C")), index=s.index)
    return cls.reindex(values.index)


def _sensitivity(e: Optional[float]) -> Optional[str]:
    if e is None:
        return None
    if e > 1.0:
        return "ELASTIC"
    if e < 1.0:
        return "INELASTIC"
    return "UNIT_ELASTIC"


class PricingOptimizationEngine:
    """Enterprise Pricing Optimization & Demand Pattern Analytics Engine."""

    def __init__(self, db: Optional[Session] = None):
        self.db = db

    def _get_db(self) -> Session:
        return self.db if self.db is not None else SessionLocal()

    # ------------------------------------------------------------------ data
    def _load_daily(self, db: Session) -> pd.DataFrame:
        # date() exists in both SQLite and PostgreSQL and truncates a timestamp to its calendar day
        day = func.date(SalesHistory.date)
        rows = (
            db.query(
                SalesHistory.product_id,
                day.label("day"),
                func.sum(SalesHistory.quantity_sold).label("qty"),
                func.sum(SalesHistory.unit_price * SalesHistory.quantity_sold).label("price_x_qty"),
                func.sum(SalesHistory.revenue).label("revenue"),
                func.count(SalesHistory.id).label("rows"),
            )
            .group_by(SalesHistory.product_id, day)
            .all()
        )
        df = pd.DataFrame(rows, columns=["product_id", "day", "qty", "price_x_qty", "revenue", "rows"])
        if df.empty:
            return df
        df["day"] = pd.to_datetime(df["day"])
        for c in ("qty", "price_x_qty", "revenue"):
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0).astype(float)
        df["rows"] = df["rows"].astype(int)
        return df

    # --------------------------------------------------------------- methods
    @staticmethod
    def _classify(daily: pd.DataFrame) -> Dict[str, Any]:
        """SBC classification of one product's daily demand (rows = days with any sales record)."""
        d = daily[daily["qty"] > 0]
        demand_days = int(len(d))
        if demand_days == 0:
            return {"pattern": "insufficient_data", "adi": None, "cv_squared": None,
                    "avg_daily_sales": None, "std_daily_sales": None, "span_days": 0, "demand_days": 0}
        span_days = int((d["day"].max() - d["day"].min()).days) + 1
        # Full daily series with zeros on days without demand
        mean_daily = float(d["qty"].sum()) / span_days
        series = np.zeros(span_days)
        idx = (d["day"] - d["day"].min()).dt.days.to_numpy()
        np.add.at(series, idx, d["qty"].to_numpy())
        std_daily = float(np.std(series, ddof=1)) if span_days > 1 else None
        if demand_days < 2:
            return {"pattern": "insufficient_data", "adi": None, "cv_squared": None,
                    "avg_daily_sales": mean_daily, "std_daily_sales": std_daily,
                    "span_days": span_days, "demand_days": demand_days}
        sizes = d["qty"].to_numpy()
        adi = span_days / demand_days
        m = float(np.mean(sizes))
        cv2 = (float(np.std(sizes, ddof=1)) / m) ** 2 if m > 0 else None
        if cv2 is None:
            pattern = "insufficient_data"
        elif adi < SBC_ADI_THRESHOLD:
            pattern = "smooth" if cv2 < SBC_CV2_THRESHOLD else "erratic"
        else:
            pattern = "intermittent" if cv2 < SBC_CV2_THRESHOLD else "lumpy"
        return {"pattern": pattern, "adi": adi, "cv_squared": cv2, "avg_daily_sales": mean_daily,
                "std_daily_sales": std_daily, "span_days": span_days, "demand_days": demand_days}

    @staticmethod
    def _fit_elasticity(daily: pd.DataFrame) -> Dict[str, Any]:
        d = daily[(daily["qty"] > 0)].copy()
        d["price"] = d["price_x_qty"] / d["qty"]
        d = d[d["price"] > 0]
        n_periods = int(len(d))
        n_prices = int(d["price"].round(2).nunique()) if n_periods else 0
        out = {"elasticity": None, "intercept": None, "r_squared": None,
               "n_points": n_periods, "n_distinct_prices": n_prices,
               "min_price": _r(d["price"].min()) if n_periods else None,
               "max_price": _r(d["price"].max()) if n_periods else None}
        if n_prices < MIN_PRICE_POINTS or n_periods < MIN_PERIODS_WITH_SALES:
            return out
        x = np.log(d["price"].to_numpy())
        y = np.log(d["qty"].to_numpy())
        X = np.column_stack([np.ones_like(x), x])
        coef, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
        a, b = float(coef[0]), float(coef[1])
        pred = X @ coef
        ss_res = float(np.sum((y - pred) ** 2))
        ss_tot = float(np.sum((y - y.mean()) ** 2))
        out.update({"elasticity": -b, "intercept": a,
                    "r_squared": (1.0 - ss_res / ss_tot) if ss_tot > 0 else None})
        return out

    @staticmethod
    def _newsvendor(mean_daily: Optional[float], std_daily: Optional[float],
                    price: Optional[float], cost: Optional[float]) -> Dict[str, Any]:
        res = {"target_quantity": None, "expected_demand": None, "demand_std": None,
               "critical_ratio": None, "z": None, "expected_profit": None,
               "expected_lost_sales": None, "expected_leftover": None,
               "shortage_risk_cost": None, "full_price_sales_ratio": None,
               "salvage_value": None, "note": None}
        if mean_daily is None or std_daily is None:
            res["note"] = "Need at least 2 days of demand history."
            return res
        if not price or not cost or price <= 0 or cost <= 0:
            res["note"] = "selling_price and unit_cost must both be > 0 in products."
            return res
        salvage = SALVAGE_FRACTION * cost
        res["salvage_value"] = salvage
        if price <= cost:
            res["note"] = "Selling price is not above unit cost; ordering does not make a profit."
            return res
        H = NEWSVENDOR_HORIZON_DAYS
        mu = mean_daily * H
        sigma = std_daily * math.sqrt(H)
        cr = (price - cost) / (price - salvage)
        res.update({"expected_demand": mu, "demand_std": sigma, "critical_ratio": cr})
        if sigma <= 0:
            q = mu
            lost, left, sales = 0.0, 0.0, mu
            z = None
        else:
            z = float(norm.ppf(cr))
            q = mu + z * sigma
            if q < 0:
                q = 0.0
            zq = (q - mu) / sigma
            lost = sigma * (float(norm.pdf(zq)) - zq * (1.0 - float(norm.cdf(zq))))  # E[(D-Q)+]
            sales = q - (q - mu + lost)  # Q - E[(Q-D)+]
            left = max(0.0, q - sales)
        profit = price * sales + salvage * left - cost * q
        res.update({
            "target_quantity": q, "z": z, "expected_profit": profit,
            "expected_lost_sales": lost, "expected_leftover": left,
            "shortage_risk_cost": lost * (price - cost),
            "full_price_sales_ratio": (sales / q * 100.0) if q > 0 else None,
        })
        return res

    # ------------------------------------------------------------------ main
    def get_pricing_intelligence(self) -> Dict[str, Any]:
        """Calculates pricing optimization & demand analytics from the database."""
        db = self._get_db()
        should_close = (self.db is None)
        try:
            products = db.query(Product).all()
            daily = self._load_daily(db)
            total_products = len(products)
            if daily.empty:
                return self._empty_response(total_products)

            prod_by_id = {p.id: p for p in products}
            daily = daily[daily["product_id"].isin(prod_by_id.keys())]
            if daily.empty:
                return self._empty_response(total_products)

            sales_rows_used = int(daily["rows"].sum())
            totals = daily.groupby("product_id").agg(revenue=("revenue", "sum"), qty=("qty", "sum"))
            rev_cls = _abc(totals["revenue"].clip(lower=0))
            qty_cls = _abc(totals["qty"].clip(lower=0))
            order = totals.sort_values("revenue", ascending=False).index.tolist()

            per = {}
            for pid, g in daily.groupby("product_id"):
                g = g.sort_values("day")
                p = prod_by_id[pid]
                cls = self._classify(g)
                el = self._fit_elasticity(g)
                rc, qc = rev_cls.get(pid), qty_cls.get(pid)
                mix = f"{rc}_{qc}" if rc and qc else None
                per[pid] = {"product": p, "cls": cls, "el": el, "mix": mix,
                            "revenue": float(totals.at[pid, "revenue"]), "qty": float(totals.at[pid, "qty"])}

            # ---- 1. demand distribution over ALL products with sales
            counts = {"smooth": 0, "intermittent": 0, "erratic": 0, "lumpy": 0, "insufficient_data": 0}
            for v in per.values():
                counts[v["cls"]["pattern"]] += 1
            classified = sum(counts[k] for k in ("smooth", "intermittent", "erratic", "lumpy"))

            sample_demand_patterns = []
            for pid in order[:DETAIL_LIST_LIMIT]:
                v = per[pid]
                c = v["cls"]
                sample_demand_patterns.append({
                    "sku_name": v["product"].name,
                    "sku_code": v["product"].sku,
                    "adi": _r(c["adi"]),
                    "cv_squared": _r(c["cv_squared"]),
                    "avg_daily_sales": _r(c["avg_daily_sales"], 2),
                    "demand_pattern": c["pattern"],
                    "product_mix": v["mix"],
                    "days_in_span": c["span_days"],
                    "days_with_demand": c["demand_days"],
                })

            # ---- 2. elasticity & price optimisation
            optimizations: List[Dict[str, Any]] = []
            elasticities: List[Dict[str, Any]] = []
            uplifts: List[float] = []
            elastic_values: List[float] = []
            valid_pstar = 0
            for pid in order:
                v = per[pid]
                p = v["product"]
                el = v["el"]
                e = el["elasticity"]
                a = el["intercept"]
                price = float(p.selling_price) if p.selling_price else None
                cost = float(p.unit_cost) if p.unit_cost else None
                p_star = None
                rec_price = None
                delta = None
                uplift = None
                uplift_unclamped = None
                clamped = False
                if e is None:
                    action = "NOT_ENOUGH_PRICE_VARIATION"
                    note = (f"Needs >= {MIN_PRICE_POINTS} distinct prices and >= {MIN_PERIODS_WITH_SALES} "
                            f"days with sales; found {el['n_distinct_prices']} prices over {el['n_points']} days.")
                else:
                    elastic_values.append(e)
                    if e <= 1.0:
                        action = "INELASTIC_NO_INTERIOR_OPTIMUM"
                        note = ("Fitted elasticity is <= 1, so the constant-elasticity model has no finite "
                                "profit-maximising price; no price is suggested.")
                    elif cost is None or cost <= 0:
                        action = "MISSING_UNIT_COST"
                        note = "unit_cost is missing or 0 in products; P* cannot be computed."
                    else:
                        p_star = cost * e / (e - 1.0)
                        valid_pstar += 1
                        note = "P* = unit_cost * e / (e - 1) from the fitted log-log curve."
                        if price is None or price <= 0:
                            action = "MISSING_SELLING_PRICE"
                            note += " selling_price is missing, so no change % or uplift."
                        else:
                            lo = price * (1 - MAX_PRICE_CHANGE_PCT / 100.0)
                            hi = price * (1 + MAX_PRICE_CHANGE_PCT / 100.0)
                            rec_price = min(max(p_star, lo), hi)
                            clamped = abs(rec_price - p_star) > 1e-9
                            delta = (rec_price - price) / price * 100.0
                            if clamped:
                                note += f" Suggested change clamped to the +/-{MAX_PRICE_CHANGE_PCT:g}% setting."

                            def profit(P: float) -> float:
                                return (P - cost) * math.exp(a) * P ** (-e)

                            cur_profit = profit(price)
                            if cur_profit > 0:
                                uplift = (profit(rec_price) - cur_profit) / cur_profit * 100.0
                                uplift_unclamped = (profit(p_star) - cur_profit) / cur_profit * 100.0
                                uplifts.append(uplift)
                            else:
                                note += " Current price is not above unit cost, so uplift % is undefined."
                            if abs(delta) < 0.5:
                                action = "HOLD_PRICE"
                            elif delta > 0:
                                action = "INCREASE_PRICE"
                            else:
                                action = "DECREASE_PRICE"

                if len(optimizations) < DETAIL_LIST_LIMIT:
                    subst = (f"${cost:.2f} * ({e:.3f} / ({e:.3f} - 1)) = ${p_star:.2f}"
                             if p_star is not None else None)
                    optimizations.append({
                        "sku_name": p.name,
                        "sku_code": p.sku,
                        "current_price": _r(price),
                        "unit_cost": _r(cost),
                        "best_model": "log-log regression" if e is not None else None,
                        # Constant-elasticity demand has no finite revenue-maximising price.
                        "optimum_revenue_price": None,
                        "optimum_profit_price": _r(p_star),
                        "recommended_price": _r(rec_price),
                        "recommended_delta_pct": _r(delta, 1),
                        "price_change_clamped": clamped if rec_price is not None else None,
                        "action": action,
                        "est_profit_uplift_pct": _r(uplift, 1),
                        "uplift_at_unclamped_optimum_pct": _r(uplift_unclamped, 1),
                        "elasticity": _r(e, 3),
                        "r_squared": _r(el["r_squared"], 3),
                        "price_points": el["n_points"],
                        "distinct_prices": el["n_distinct_prices"],
                        "calculation_trace": {
                            "formula": "log(qty) = a + b*log(price); e = -b; P* = Cost * e / (e - 1)",
                            "unit_cost": _r(cost),
                            "current_price": _r(price),
                            "elasticity": _r(e, 3),
                            "elasticity_type": _sensitivity(e),
                            "intercept_a": _r(a, 4),
                            "r_squared": _r(el["r_squared"], 3),
                            "n_points": el["n_points"],
                            "n_distinct_prices": el["n_distinct_prices"],
                            "observed_price_range": [el["min_price"], el["max_price"]],
                            "substitution": subst,
                            "data_source_tables": "products (unit_cost, selling_price), sales_history (date, quantity_sold, unit_price)",
                            "explanation": note,
                        },
                    })
                if len(elasticities) < DETAIL_LIST_LIMIT:
                    elasticities.append({
                        "sku_name": p.name,
                        "sku_code": p.sku,
                        "elasticity": _r(e, 3),
                        "sensitivity": _sensitivity(e),
                        "optimum_price_profit": _r(p_star),
                        "optimum_price_revenue": None,
                        "r_squared": _r(el["r_squared"], 3),
                        "n_points": el["n_points"],
                        "n_distinct_prices": el["n_distinct_prices"],
                        "calculation_trace": {
                            "formula": "Least-squares fit of log(daily qty) on log(daily qty-weighted avg unit_price); e = -slope",
                            "value": _r(e, 3),
                            "interpretation": (f"A 1% price increase is associated with a {e:.2f}% change in quantity "
                                               f"in the opposite direction (r^2 = {el['r_squared']:.2f}, {el['n_points']} days)."
                                               if e is not None and el["r_squared"] is not None else
                                               ("Not enough price variation in sales_history to estimate elasticity."
                                                if e is None else None)),
                        },
                    })

            # ---- 3. newsvendor
            newsvendor_samples = []
            for pid in order[:DETAIL_LIST_LIMIT]:
                v = per[pid]
                p = v["product"]
                c = v["cls"]
                price = float(p.selling_price) if p.selling_price else None
                cost = float(p.unit_cost) if p.unit_cost else None
                nv = self._newsvendor(c["avg_daily_sales"], c["std_daily_sales"], price, cost)
                cu = (price - cost) if price and cost else None
                co = (cost - nv["salvage_value"]) if cost and nv["salvage_value"] is not None else None
                subst = None
                if nv["target_quantity"] is not None and nv["z"] is not None:
                    subst = (f"{nv['expected_demand']:.1f} + ({nv['z']:.3f} * {nv['demand_std']:.1f}) "
                             f"= {nv['target_quantity']:.1f} units")
                newsvendor_samples.append({
                    "sku_name": p.name,
                    "sku_code": p.sku,
                    "target_quantity": _r(nv["target_quantity"], 1),
                    "expected_demand": _r(nv["expected_demand"], 1),
                    "demand_std": _r(nv["demand_std"], 1),
                    "shortage_risk_cost": _r(nv["shortage_risk_cost"]),
                    "unit_cost": _r(cost),
                    "selling_price": _r(price),
                    "salvage_value": _r(nv["salvage_value"]),
                    "expected_profit": _r(nv["expected_profit"]),
                    "expected_lost_sales": _r(nv["expected_lost_sales"], 1),
                    "expected_leftover": _r(nv["expected_leftover"], 1),
                    "full_price_sales_ratio": _r(nv["full_price_sales_ratio"], 1),
                    "horizon_days": NEWSVENDOR_HORIZON_DAYS,
                    "calculation_trace": {
                        "critical_fractile_formula": "CR = (Price - Cost) / (Price - Salvage) = Cu / (Cu + Co)",
                        "underage_cost_Cu": _r(cu),
                        "overage_cost_Co": _r(co),
                        "critical_fractile": _r(nv["critical_ratio"], 3),
                        "z_score": _r(nv["z"], 3),
                        "target_order_formula": "Q* = mean_daily*H + z(CR) * std_daily*sqrt(H)",
                        "daily_demand_mean": _r(c["avg_daily_sales"], 3),
                        "daily_demand_std": _r(c["std_daily_sales"], 3),
                        "history_days": c["span_days"],
                        "substitution": subst,
                        "expected_profit_formula": "Price*E[sales] + Salvage*E[leftover] - Cost*Q (normal demand, scipy.stats.norm)",
                        "data_source_tables": "products (selling_price, unit_cost), sales_history (date, quantity_sold)",
                        "note": nv["note"],
                    },
                })

            avg_el = _r(float(np.mean(elastic_values)), 3) if elastic_values else None
            avg_uplift = _r(float(np.mean(uplifts)), 1) if uplifts else None

            # ---- recommendations (real numbers only)
            recommendations = []
            ranked = sorted([o for o in optimizations if o["est_profit_uplift_pct"] is not None],
                            key=lambda o: o["est_profit_uplift_pct"], reverse=True)
            for o in ranked[:5]:
                if o["est_profit_uplift_pct"] <= 0:
                    continue
                recommendations.append({
                    "title": f"{o['sku_code']}: move price from ${o['current_price']:.2f} to ${o['recommended_price']:.2f}",
                    "impact": f"{o['est_profit_uplift_pct']:+.1f}% modelled profit",
                    "details": (f"Price elasticity {o['elasticity']:.2f} from {o['price_points']} daily price points "
                                f"({o['distinct_prices']} distinct prices, r^2={o['r_squared']:.2f}); profit-optimal price "
                                f"${o['optimum_profit_price']:.2f} vs ${o['current_price']:.2f} today"
                                + (f" (change limited to +/-{MAX_PRICE_CHANGE_PCT:g}%)." if o["price_change_clamped"] else ".")),
                    "urgency": "HIGH" if o["r_squared"] is not None and o["r_squared"] >= 0.5 else "MEDIUM",
                })
            sparse = counts["lumpy"] + counts["intermittent"]
            if sparse > 0:
                recommendations.append({
                    "title": "Use newsvendor / buffer-stock ordering for lumpy and intermittent SKUs",
                    "impact": f"{sparse} of {classified} classified SKUs",
                    "details": (f"{counts['lumpy']} lumpy and {counts['intermittent']} intermittent products "
                                f"(ADI >= {SBC_ADI_THRESHOLD}) from their daily sales history."),
                    "urgency": "MEDIUM",
                })

            return {
                "module_name": "Advance Analytics & Pricing Optimization",
                "module_key": "advance_analytics",
                "database_info": {
                    "is_connected": True,
                    "source": "Connected database (products, sales_history)",
                    "total_products": total_products,
                    "products_with_sales": len(per),
                    "products_analysed": len(per),
                    "sales_records_analyzed": sales_rows_used,
                    "fallback_used": False,
                },
                "settings": _settings(),
                "calculation_trace": {
                    "methodology": "Log-log price elasticity regression + profit optimisation (P* = Cost * e / (e - 1))",
                    "elasticity_formula": "log(daily qty) = a + b*log(daily avg unit_price), e = -b (numpy least squares)",
                    "profit_maximization_formula": "P* = Unit_Cost * [e / (e - 1)], only when e > 1",
                    "uplift_formula": "q(P) = exp(a)*P^(-e); profit(P) = (P - cost)*q(P); uplift = (profit(P_rec) - profit(P_now)) / profit(P_now)",
                    "demand_classification_formula": (f"Syntetos-Boylan-Croston on daily series: ADI = span days / demand days, "
                                                      f"CV^2 of non-zero daily sizes; thresholds ADI {SBC_ADI_THRESHOLD}, CV^2 {SBC_CV2_THRESHOLD}"),
                    "abc_formula": (f"ABC on cumulative revenue share and quantity share (A <= {ABC_A_CUTOFF:.0%}, "
                                    f"B <= {ABC_B_CUTOFF:.0%}, C rest); product_mix = revenue class _ quantity class"),
                    "newsvendor_critical_ratio": "CR = (Price - Cost) / (Price - Salvage); Q* = mu_H + z(CR)*sigma_H",
                    "data_source_tables": "products (selling_price, unit_cost), sales_history (quantity_sold, unit_price, revenue, date)",
                    "explanation": ("Elasticity is fitted per product from days with different prices in sales_history; products "
                                    "without enough price variation get null. Summary averages use only products with an estimate."),
                },
                "summary": {
                    "total_skus_classified": classified,
                    "insufficient_data_skus": counts["insufficient_data"],
                    "optimized_sku_count": valid_pstar,
                    "elasticity_estimated_count": len(elastic_values),
                    "avg_price_elasticity": avg_el,
                    "avg_profit_uplift_potential_pct": avg_uplift,
                    "smooth_demand_pct": _r(counts["smooth"] / classified * 100, 1) if classified else None,
                    "lumpy_or_intermittent_pct": _r(sparse / classified * 100, 1) if classified else None,
                    "primary_model": "Syntetos-Boylan-Croston + log-log elasticity regression",
                },
                "optimizations": optimizations,
                "elasticities": elasticities,
                "demand_distribution": [
                    {"name": k.capitalize(), "count": counts[k], "color": _COLORS[k], "desc": _DESCS[k],
                     "pct": _r(counts[k] / classified * 100, 1) if classified else None}
                    for k in ("smooth", "intermittent", "erratic", "lumpy")
                ],
                "sample_demand_patterns": sample_demand_patterns,
                "newsvendor_samples": newsvendor_samples,
                "recommendations": recommendations,
            }
        finally:
            if should_close:
                db.close()

    def _empty_response(self, total_products: int = 0) -> Dict[str, Any]:
        return {
            "module_name": "Advance Analytics & Pricing Optimization",
            "module_key": "advance_analytics",
            "database_info": {
                "is_connected": True,
                "source": "Connected database (products, sales_history)",
                "total_products": total_products,
                "products_with_sales": 0,
                "products_analysed": 0,
                "sales_records_analyzed": 0,
                "fallback_used": False,
            },
            "settings": _settings(),
            "calculation_trace": {
                "methodology": "Log-log price elasticity regression + profit optimisation (P* = Cost * e / (e - 1))",
                "explanation": "No sales_history rows found, so nothing could be computed.",
            },
            "summary": {
                "total_skus_classified": 0,
                "insufficient_data_skus": 0,
                "optimized_sku_count": 0,
                "elasticity_estimated_count": 0,
                "avg_price_elasticity": None,
                "avg_profit_uplift_potential_pct": None,
                "smooth_demand_pct": None,
                "lumpy_or_intermittent_pct": None,
                "primary_model": "Syntetos-Boylan-Croston + log-log elasticity regression",
            },
            "optimizations": [],
            "elasticities": [],
            "demand_distribution": [],
            "sample_demand_patterns": [],
            "newsvendor_samples": [],
            "recommendations": [],
        }
