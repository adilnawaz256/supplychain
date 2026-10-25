"""4. Pricing & Demand: price elasticity from weekly price/volume, profit-optimal price, demand pattern."""
from typing import Dict

import numpy as np
import pandas as pd

from ._common import Data, NeedsData, col, demand_class, kpi, money, num, page, pct, short

MIN_WEEKS = 8
MIN_PRICE_POINTS = 3
MIN_PRICE_SPREAD = 0.02
MIN_R2 = 0.25            # the price/volume line must explain at least 25% of the variation
ELASTICITY_RANGE = (-5.0, -0.1)
MAX_PRICE_CHANGE = 0.25


def _optimal_price(e: float, cost: float, p0: float) -> float:
    """Constant-elasticity profit optimum p* = c·e/(e+1) (e < -1), capped to ±25% of today's price."""
    if e < -1:
        target = cost * e / (e + 1)
    else:
        target = p0 * (1 + MAX_PRICE_CHANGE)  # inelastic: profit rises with price up to the cap
    return float(np.clip(target, p0 * (1 - MAX_PRICE_CHANGE), p0 * (1 + MAX_PRICE_CHANGE)))


def compute(d: Data) -> Dict:
    s = d.sales
    if s.empty:
        raise NeedsData("sales history")
    p = d.product_costs().set_index("product_id")
    s = s.assign(week=(s["date"] - pd.to_timedelta(s["date"].dt.weekday, unit="D")).dt.normalize())
    wk = s.groupby(["product_id", "week"]).agg(units=("qty", "sum"), revenue=("revenue", "sum")).reset_index()
    wk = wk[wk["units"] > 0]
    wk["price"] = wk["revenue"] / wk["units"]
    last_week = s["week"].max()

    rows, curves = [], {}
    for pid, g in wk.groupby("product_id"):
        info = p.loc[pid] if pid in p.index else None
        if info is None:
            continue
        life_weeks = int((last_week - g["week"].min()).days // 7) + 1
        series = np.zeros(max(life_weeks, len(g)))
        series[: len(g)] = g["units"].to_numpy()  # order is irrelevant for ADI / CV²
        p0 = float(g["revenue"].sum() / g["units"].sum())
        q0 = float(g["units"].sum() / len(series))
        cost = float(info["unit_cost"]) if info["unit_cost"] > 0 else p0 * 0.6
        row = {"sku": info["sku"], "product": info["name"], "category": info["category"], "unit_cost": cost,
               "current_price": p0, "current_demand": q0, "demand_type": demand_class(series),
               "optimal_price": None, "elasticity": None, "optimal_demand": None,
               "revenue_change": None, "profit_change": None, "profit_gain": None, "opportunity": "Not measurable"}
        prices = g["price"].round(2)
        spread = (prices.max() - prices.min()) / prices.mean() if prices.mean() > 0 else 0
        if len(g) >= MIN_WEEKS and prices.nunique() >= MIN_PRICE_POINTS and spread >= MIN_PRICE_SPREAD:
            x, y = np.log(g["price"].to_numpy()), np.log(g["units"].to_numpy())
            b, a = np.polyfit(x, y, 1)
            resid = y - (a + b * x)
            r2 = 1 - resid.var() / y.var() if y.var() > 0 else 0.0
            if ELASTICITY_RANGE[0] < b < 0 and r2 >= MIN_R2 and p0 <= cost:
                row.update(elasticity=float(b), fit_r2=float(r2), opportunity="Below cost")
            elif ELASTICITY_RANGE[0] < b < 0 and r2 >= MIN_R2:
                e = float(np.clip(b, *ELASTICITY_RANGE))
                row["fit_r2"] = float(r2)
                p1 = _optimal_price(e, cost, p0)
                q1 = q0 * (p1 / p0) ** e
                rev0, rev1 = p0 * q0, p1 * q1
                prof0, prof1 = (p0 - cost) * q0, (p1 - cost) * q1
                profit_change = (prof1 - prof0) / abs(prof0) * 100 if prof0 else None
                row.update(optimal_price=p1, elasticity=e, optimal_demand=q1,
                           revenue_change=(rev1 - rev0) / rev0 * 100 if rev0 else None,
                           profit_change=profit_change, profit_gain=(prof1 - prof0) * 52,
                           opportunity=("High" if (profit_change or 0) >= 10 else
                                        "Medium" if (profit_change or 0) >= 3 else "Low"))
                xs = np.linspace(p0 * 0.5, p0 * 1.5, 15)
                curves[pid] = {"curve": [{"x": float(x), "y": float(np.exp(a) * x ** e)} for x in xs],
                               "points": [{"x": float(r.price), "y": float(r.units)} for r in g.itertuples()],
                               "p0": p0, "p1": p1, "q0": q0, "q1": q1, "cost": cost}
        rows.append(row)

    if not rows:
        raise NeedsData("sales history")
    df = pd.DataFrame(rows)
    n_priced = int(df["elasticity"].notna().sum())
    below_cost = int((df["opportunity"] == "Below cost").sum())
    priced = df[df["optimal_price"].notna()]

    if len(priced):
        rev0 = (priced["current_price"] * priced["current_demand"]).sum()
        rev1 = (priced["optimal_price"] * priced["optimal_demand"]).sum()
        cost_by = priced["unit_cost"]
        prof0 = ((priced["current_price"] - cost_by) * priced["current_demand"]).sum()
        prof1 = ((priced["optimal_price"] - cost_by) * priced["optimal_demand"]).sum()
        rev_opp = (rev1 - rev0) / rev0 * 100 if rev0 else None
        prof_opp = (prof1 - prof0) / abs(prof0) * 100 if prof0 else None
        median_e = float(priced["elasticity"].median())
        cat = priced.groupby("category")["profit_gain"].sum().sort_values(ascending=False)
        cat_base = (priced.assign(b=(priced["current_price"] - cost_by) * priced["current_demand"] * 52)
                    .groupby("category")["b"].sum())
        top_cat = cat.index[0]
        top_cat_pct = cat.iloc[0] / abs(cat_base[top_cat]) * 100 if cat_base[top_cat] else None
        elastic = priced[priced["elasticity"] < -1]
        pool = elastic if len(elastic) else priced
        ex_sku = pool.loc[pool["profit_gain"].idxmax(), "sku"]
    else:
        rev_opp = prof_opp = median_e = top_cat_pct = None
        top_cat, ex_sku = "—", None

    ex_pid = p.index[p["sku"] == ex_sku][0] if ex_sku is not None else None
    ex = curves.get(ex_pid)
    ex_name = short(p.loc[ex_pid, "name"], 32) if ex_pid is not None else ""
    compare_rows = []
    if ex:
        def change(a, b):
            return f"{(b - a) / abs(a) * 100:+.1f}%" if a else "—"
        prof_a, prof_b = (ex["p0"] - ex["cost"]) * ex["q0"], (ex["p1"] - ex["cost"]) * ex["q1"]
        compare_rows = [
            {"metric": "Price", "current": money(ex["p0"]), "optimal": money(ex["p1"]), "change": change(ex["p0"], ex["p1"])},
            {"metric": "Weekly demand", "current": num(ex["q0"], 1), "optimal": num(ex["q1"], 1), "change": change(ex["q0"], ex["q1"])},
            {"metric": "Weekly revenue", "current": money(ex["p0"] * ex["q0"]), "optimal": money(ex["p1"] * ex["q1"]),
             "change": change(ex["p0"] * ex["q0"], ex["p1"] * ex["q1"])},
            {"metric": "Weekly profit", "current": money(prof_a), "optimal": money(prof_b), "change": change(prof_a, prof_b)},
        ]

    cats = df["category"].value_counts().index[:5].tolist()
    scatter_df = df[df["current_demand"] > 0].nlargest(600, "current_demand")
    groups = []
    for c in cats + ["Other"]:
        part = scatter_df[scatter_df["category"] == c] if c != "Other" else scatter_df[~scatter_df["category"].isin(cats)]
        if len(part):
            groups.append({"name": c, "points": [{"x": float(r.current_price), "y": float(r.current_demand), "label": r.product}
                                                 for r in part.itertuples() if r.current_price > 0]})

    pattern = df["demand_type"].value_counts()
    return page(
        input_={"title": "Sales & price history (sales_history)",
                "scope": f"All warehouses · {len(d.sales):,} rows · {len(df):,} products",
                "columns": "Product, Date, Quantity, Unit price, Revenue, Unit cost"},
        algorithm={"title": "Price Elasticity + Optimal Price",
                   "description": f"log(weekly units) vs log(weekly price) gives elasticity (kept when R² ≥ {MIN_R2}); profit-optimal price = cost × e ÷ (e + 1), capped at ±25%; ADI / CV² classify demand."},
        output={"title": "pricing_demand_results",
                "description": "Elasticity, optimal price, expected demand, revenue and profit change per product."},
        kpis=[
            kpi("Products Analyzed", num(len(df)), f"{n_priced:,} with measurable price response", "info", "box"),
            kpi("Avg. Price Elasticity", f"{median_e:.2f}" if median_e is not None else "—",
                ("Demand is elastic" if median_e < -1 else "Demand is inelastic") if median_e is not None else "Needs price changes",
                "info", "chart"),
            kpi("Revenue Opportunity", pct(rev_opp, signed=True) if rev_opp is not None else "—", "By optimal pricing",
                "good" if (rev_opp or 0) >= 0 else "warn", "trending", "up" if (rev_opp or 0) >= 0 else "down"),
            kpi("Profit Opportunity", pct(prof_opp, signed=True) if prof_opp is not None else "—", "By optimal pricing",
                "good", "database", "up" if (prof_opp or 0) > 0 else None),
            kpi("Top Opportunity Category", str(top_cat),
                f"{pct(top_cat_pct, signed=True)} profit potential" if top_cat_pct is not None else
                f"{int(pattern.get('Intermittent', 0) + pattern.get('Lumpy', 0)):,} products sell irregularly",
                "warn", "trophy", "up" if top_cat_pct else None),
        ],
        charts=[
            {"type": "curve", "title": f"Demand Curve ({ex_name})" if ex else "Demand Curve (Example Product)",
             "xLabel": "Price", "yLabel": "Weekly units", "curve": ex["curve"] if ex else [],
             "points": ex["points"] if ex else [], "empty": "No product changed price enough to fit a demand curve."},
            {"type": "compare", "title": "Optimal Price Analysis", "subtitle": ex_name,
             "columns": [{"key": "metric", "label": "Metric"}, {"key": "current", "label": "Current"},
                         {"key": "optimal", "label": "Optimal"}, {"key": "change", "label": "Change"}],
             "rows": compare_rows, "empty": "Needs sales at several different prices."},
            {"type": "scatter", "title": "Price vs. Demand (All Products)", "xLabel": "Avg price", "yLabel": "Weekly units",
             "xLog": True, "yLog": True, "groups": groups, "xFormat": "money"},
        ],
        table={
            "title": "Pricing & Demand Results", "searchPlaceholder": "Search products...",
            "columns": [
                col("sku", "Product ID"), col("product", "Product Name"), col("category", "Category"),
                col("current_price", "Current Price", "money"), col("optimal_price", "Optimal Price", "money"),
                col("elasticity", "Price Elasticity", "num2"), col("fit_r2", "Fit R²", "num2", hidden=True),
                col("current_demand", "Current Demand", "num"), col("optimal_demand", "Optimal Demand", "num"),
                col("revenue_change", "Revenue Change", "pct_signed"),
                col("profit_change", "Profit Change", "pct_signed", hidden=True),
                col("demand_type", "Demand Type", "pill", hidden=True,
                    pills={"Smooth": "good", "Erratic": "warn", "Intermittent": "info", "Lumpy": "bad"}),
                col("opportunity", "Opportunity", "trend",
                    trends={"High": "up", "Medium": "ok", "Low": "down", "Not measurable": "none", "Below cost": "down"}),
            ],
            "filters": ["category", "opportunity", "demand_type"],
            "sort": {"key": "profit_gain", "dir": "desc"},
            "rows": df.to_dict("records"),
        },
        notes=[f"Demand is weekly units per product. Only {n_priced:,} of {len(df):,} products sold at "
               f"{MIN_PRICE_POINTS}+ different prices over {MIN_WEEKS}+ weeks with a clear price response "
               f"(fit R² ≥ {MIN_R2}), so only they get a price suggestion."]
              + ([f"{below_cost:,} of them sell at or below their recorded unit cost; they are marked 'Below cost' "
                  "and left out of the profit maths (check the cost or the price)."] if below_cost else []),
    )
