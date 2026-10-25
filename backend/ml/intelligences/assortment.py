"""8. Assortment Planning: shift category / product space towards higher profit per unit of space."""
from typing import Dict

import numpy as np
import pandas as pd

from ._common import Data, NeedsData, col, kpi, money, num, page, pct, short

WINDOW_DAYS = 365
SPACE_ELASTICITY = 0.3   # +10% space -> about +3% sales (common retail assumption)
MAX_SHIFT = 0.5          # a category or product can grow or shrink its space by at most 50%
CHANGE_THRESHOLD = 10.0  # % change in space that counts as Increase / Reduce


def _rebalance(space: pd.Series, density: pd.Series) -> pd.Series:
    """Move space towards higher profit density, within ±MAX_SHIFT of today, keeping the total fixed."""
    avg = (density * space).sum() / space.sum() if space.sum() else 0
    if avg <= 0:
        return space.copy()
    factor = np.sqrt((density / avg).clip(lower=0.01))
    lo, hi = space * (1 - MAX_SHIFT), space * (1 + MAX_SHIFT)
    new = (space * factor).clip(lo, hi)
    for _ in range(10):
        new = (new * space.sum() / new.sum()).clip(lo, hi)
    return new * space.sum() / new.sum()


def compute(d: Data) -> Dict:
    s = d.sales
    if s.empty:
        raise NeedsData("sales history")
    s = s[s["date"] >= s["date"].max() - pd.Timedelta(days=WINDOW_DAYS)]
    p = d.product_costs().set_index("product_id")
    g = s.groupby("product_id").agg(units=("qty", "sum"), revenue=("revenue", "sum"))
    g = g.join(p[["sku", "name", "category", "unit_cost"]], how="inner")
    g["profit"] = g["revenue"] - g["units"] * g["unit_cost"]

    rs = d.retail_spaces
    real_space = not rs.empty
    if real_space:
        space = rs.groupby("product_id")["allocated_space_sqm"].sum()
        g["space"] = g.index.map(space)
        g = g[g["space"].fillna(0) > 0]
        unit = "m²"
    else:
        g["space"] = 1.0  # no shelf data: every active product takes one slot
        unit = "SKU slots"
    if g.empty:
        raise NeedsData("sales for products with shelf space")

    cat = g.groupby("category").agg(space=("space", "sum"), revenue=("revenue", "sum"), profit=("profit", "sum"),
                                    products=("sku", "count"))
    cat["density"] = cat["profit"] / cat["space"]
    cat["new_space"] = _rebalance(cat["space"], cat["density"])
    ratio = cat["new_space"] / cat["space"]
    cat["exp_revenue"] = cat["revenue"] * ratio ** SPACE_ELASTICITY
    cat["exp_profit"] = cat["profit"] * ratio ** SPACE_ELASTICITY
    total_space = cat["space"].sum()

    # Products: rebalance inside each category, then scale to that category's new space.
    parts = []
    for c, grp in g.groupby("category"):
        new = _rebalance(grp["space"], grp["profit"] / grp["space"])
        parts.append(new * cat.loc[c, "new_space"] / cat.loc[c, "space"])
    g["new_space"] = pd.concat(parts)
    r = g["new_space"] / g["space"]
    g["exp_revenue"] = g["revenue"] * r ** SPACE_ELASTICITY
    g["exp_profit"] = g["profit"] * r ** SPACE_ELASTICITY
    cat_space = g["category"].map(cat["space"])
    cat_new = g["category"].map(cat["new_space"])
    g["cur_pct"] = g["space"] / cat_space * 100
    g["rec_pct"] = g["new_space"] / cat_new * 100
    g["space_change"] = (g["new_space"] / g["space"] - 1) * 100
    g["margin"] = np.where(g["revenue"] > 0, g["profit"] / g["revenue"] * 100, np.nan)
    g["recommendation"] = np.where(g["profit"] <= 0, "Review",
                                   np.where(g["space_change"] >= CHANGE_THRESHOLD, "Increase",
                                            np.where(g["space_change"] <= -CHANGE_THRESHOLD, "Reduce", "Maintain")))

    rev0, rev1 = cat["revenue"].sum(), cat["exp_revenue"].sum()
    prof0, prof1 = cat["profit"].sum(), cat["exp_profit"].sum()
    sales_up = (rev1 / rev0 - 1) * 100 if rev0 else None
    profit_up = (prof1 / prof0 - 1) * 100 if prof0 > 0 else None
    changes = int((g["recommendation"] != "Maintain").sum())
    cat_moves = int(((cat["new_space"] / cat["space"] - 1).abs() * 100 >= 1).sum())

    top_cats = cat.sort_values("revenue", ascending=False)
    shown = top_cats.head(6)
    space_chart = [{"name": c, "current": float(v.space / total_space * 100), "optimized": float(v.new_space / total_space * 100)}
                   for c, v in shown.iterrows()]
    sales_chart = [{"name": c, "sales": float(v.exp_revenue), "profit": float(v.exp_profit)} for c, v in shown.iterrows()]
    if len(top_cats) > 6:
        rest = top_cats.iloc[6:]
        space_chart.append({"name": "Other", "current": float(rest["space"].sum() / total_space * 100),
                            "optimized": float(rest["new_space"].sum() / total_space * 100)})
        sales_chart.append({"name": "Other", "sales": float(rest["exp_revenue"].sum()), "profit": float(rest["exp_profit"].sum())})
    adds = g[g["recommendation"] == "Increase"].nlargest(10, "space_change")

    rows = g.reset_index(drop=True)[["sku", "name", "category", "cur_pct", "rec_pct", "space_change", "exp_revenue",
                                     "exp_profit", "margin", "recommendation"]].rename(columns={"name": "product"})
    return page(
        input_={"title": "Product, sales & space data (sales_history, retail_spaces)",
                "scope": f"Last {WINDOW_DAYS} days · {len(g):,} products · {len(cat):,} categories",
                "columns": "Product, Category, Revenue, Units, Unit cost, Shelf space" if real_space else
                           "Product, Category, Revenue, Units, Unit cost (no shelf data: 1 slot per product)"},
        algorithm={"title": "Assortment Optimization (Profit density + Space allocation)",
                   "description": f"Profit per {unit.rstrip('s')} decides where space moves (max ±{int(MAX_SHIFT * 100)}%, total fixed); expected sales follow space with elasticity {SPACE_ELASTICITY}."},
        output={"title": "assortment_planning_results",
                "description": "Current vs recommended space, expected sales and profit per category and product."},
        kpis=[
            kpi("Total Products Analyzed", num(len(g)), f"Across {len(cat):,} categories", "info", "box"),
            kpi("Total Shelf Space", f"{num(total_space)} {unit}", "Kept the same, only re-allocated", "good", "store"),
            kpi("Projected Sales Increase", pct(sales_up, signed=True) if sales_up is not None else "—",
                f"{money(rev1 - rev0)} additional revenue", "good", "chart", "up" if (sales_up or 0) > 0 else None),
            kpi("Projected Profit Increase", pct(profit_up, signed=True) if profit_up is not None else "—",
                f"{money(prof1 - prof0)} additional profit", "good", "trending", "up" if (profit_up or 0) > 0 else None),
            kpi("Category Recommendations", num(cat_moves), f"{changes:,} product adjustments suggested", "warn", "bulb"),
        ],
        charts=[
            {"type": "bar", "title": "Category Space Allocation", "data": space_chart, "valueFormat": "pct0",
             "series": [{"key": "current", "label": "Current Space", "color": "#c4b5fd"},
                        {"key": "optimized", "label": "Optimized Space", "color": "#7c3aed"}]},
            {"type": "bar", "title": "Expected Sales vs. Profit by Category", "data": sales_chart, "valueFormat": "money",
             "series": [{"key": "sales", "label": "Sales", "color": "#3b82f6"},
                        {"key": "profit", "label": "Profit", "color": "#34d399"}]},
            {"type": "hbar", "title": "Top Products to Add / Increase",
             "data": [{"name": short(r.name, 22), "label": r.name, "value": float(r.space_change)} for r in adds.itertuples()],
             "valueFormat": "pct_signed", "color": "#10b981", "wideLabels": True},
        ],
        table={
            "title": "Assortment Planning Results", "searchPlaceholder": "Search products...",
            "columns": [
                col("sku", "Product ID"), col("product", "Product Name"), col("category", "Category"),
                col("cur_pct", "Current Space %", "pct", info="Share of its category's space"),
                col("rec_pct", "Recommended Space %", "pct"),
                col("space_change", "Space Change", "pct_signed"),
                col("exp_revenue", "Expected Sales", "money"), col("exp_profit", "Expected Profit", "money"),
                col("margin", "Margin", "pct", hidden=True),
                col("recommendation", "Recommendation", "pill",
                    pills={"Increase": "good", "Maintain": "info", "Reduce": "warn", "Review": "bad"}),
            ],
            "filters": ["category", "recommendation"],
            "sort": {"key": "exp_revenue", "dir": "desc"},
            "rows": rows.to_dict("records"),
        },
        notes=([] if real_space else
               ["No shelf-space data (retail_spaces) yet, so each selling product counts as one slot of space."])
              + [f"Sales response to space uses an assumed elasticity of {SPACE_ELASTICITY}; treat changes as a pilot, not a rule."],
    )
