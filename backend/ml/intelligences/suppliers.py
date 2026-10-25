"""7. Supplier Segmentation: spend vs risk (lead time, on-time delivery, single sourcing) per supplier."""
from typing import Dict

import numpy as np
import pandas as pd

from ._common import Data, NeedsData, col, kpi, money, num, page, pct

SEGMENTS = ["Strategic", "Core", "Tactical", "At Risk"]
RECOMMEND = {"Strategic": "Increase volume", "Core": "Maintain", "Tactical": "Negotiate cost", "At Risk": "Find alternative"}
COLORS = {"Strategic": "#10b981", "Core": "#3b82f6", "Tactical": "#f59e0b", "At Risk": "#ef4444"}


def compute(d: Data) -> Dict:
    sup = d.suppliers.copy()
    if sup.empty:
        raise NeedsData("suppliers")
    links = d.supplier_products
    prods = d.product_costs().set_index("product_id")
    sales = d.sales
    units = sales.groupby("product_id")["qty"].sum() if not sales.empty else pd.Series(dtype=float)

    risk_cols = ["availability_risk", "supplier_count_risk", "standardization_risk", "price_volatility_risk"]
    # Product supply-risk index (Kraljic): sum of the four 0–0.5 risk factors, when the data has them.
    prods["risk_index"] = prods[risk_cols].sum(axis=1, min_count=1)
    has_risk = prods["risk_index"].notna().any()
    if not links.empty:
        n_sources = links.groupby("product_id")["supplier_id"].nunique()
        lk = links.assign(
            cost=lambda x: x["unit_cost"].where(x["unit_cost"] > 0, x["product_id"].map(prods["unit_cost"])),
            units=lambda x: x["product_id"].map(units).fillna(0) / x["product_id"].map(n_sources),
            single=lambda x: x["product_id"].map(n_sources) == 1,
            category=lambda x: x["product_id"].map(prods["category"]),
            lt=lambda x: x["product_id"].map(prods["lead_time_days"]),
            lt_sd=lambda x: x["product_id"].map(prods["lead_time_sd_days"]),
            risk_index=lambda x: x["product_id"].map(prods["risk_index"]),
        )
        lk["spend"] = lk["cost"].fillna(0) * lk["units"]
        if has_risk:
            spend_cut, risk_cut = lk["spend"].median(), lk["risk_index"].median()
            hi_risk = lk["risk_index"] > risk_cut
            lk["strategic_item"] = hi_risk & (lk["spend"] > spend_cut)
            lk["critical_item"] = hi_risk & (lk["spend"] <= spend_cut)
            lk["w_risk"] = lk["risk_index"] * lk["spend"].clip(lower=0.01)
            lk["w"] = lk["spend"].clip(lower=0.01).where(lk["risk_index"].notna())
        else:
            lk["strategic_item"] = lk["critical_item"] = False
            lk["w_risk"] = lk["w"] = np.nan
        agg = lk.groupby("supplier_id").agg(products=("product_id", "nunique"), categories=("category", "nunique"),
                                            sales_spend=("spend", "sum"), avg_cost=("cost", "mean"),
                                            single=("single", "mean"), link_lt=("lt", "mean"), lt_sd=("lt_sd", "mean"),
                                            strategic_items=("strategic_item", "sum"), critical_items=("critical_item", "sum"),
                                            w_risk=("w_risk", "sum"), w=("w", "sum"))
        agg["product_risk"] = agg["w_risk"] / agg["w"].replace(0, np.nan)
        sup = sup.join(agg, on="supplier_id")
    for c in ["products", "categories", "sales_spend", "avg_cost", "single", "link_lt", "lt_sd", "strategic_items",
              "critical_items", "product_risk"]:
        if c not in sup:
            sup[c] = np.nan
    po = d.purchase_orders.groupby("supplier_id")["total_cost"].sum() if not d.purchase_orders.empty else pd.Series(dtype=float)
    sup["po_spend"] = sup["supplier_id"].map(po)
    sup["spend"] = sup["po_spend"].where(sup["po_spend"] > 0, sup["sales_spend"]).fillna(0)
    # Imported suppliers all get the same default lead time; then the lead times of their products are the real signal.
    own_lt = sup["lead_time_avg_days"].where(sup["lead_time_avg_days"] > 0)
    sup["lead_time"] = (own_lt.fillna(sup["link_lt"]) if own_lt.nunique() > 1 or sup["link_lt"].isna().all()
                        else sup["link_lt"].fillna(own_lt))
    otif = sup["otif_score"].astype(float)
    sup["otif"] = np.where(otif <= 1, otif * 100, otif)
    sup[["products", "categories"]] = sup[["products", "categories"]].fillna(0)
    sup["single"] = sup["single"].fillna(0) * 100
    has_otif = sup["otif"].notna().any()

    lt_risk = (sup["lead_time"].fillna(sup["lead_time"].median()).fillna(7) / 60).clip(0, 1)
    otif_risk = ((100 - sup["otif"]) / 50).clip(0, 1)
    single_risk = sup["single"] / 100
    if sup["product_risk"].notna().any():
        # Product supply-risk index (0–2) + lead time + lead-time variability (sd ÷ mean)
        lt_var = (sup["lt_sd"] / sup["lead_time"].replace(0, np.nan)).fillna(0).clip(0, 1)
        risk = 0.5 * (sup["product_risk"].fillna(sup["product_risk"].median()) / 2) + 0.3 * lt_risk + 0.2 * lt_var
        if sup["otif"].notna().any():
            risk = np.where(sup["otif"].notna(), 0.8 * risk + 0.2 * otif_risk, risk)
    else:
        risk = np.where(sup["otif"].notna(), 0.4 * lt_risk + 0.4 * otif_risk + 0.2 * single_risk,
                        0.6 * lt_risk + 0.4 * single_risk)
    sup["risk_score"] = np.asarray(risk, dtype=float) * 100
    # Risk level and segment are relative to the other suppliers (Kraljic-style medians), so the split stays
    # meaningful when every supplier has a similar absolute risk (e.g. every product single-sourced).
    median_spend = sup["spend"].median()
    median_risk = sup["risk_score"].median()
    low_cut = sup["risk_score"].quantile(1 / 3)
    sup["risk_level"] = np.where(sup["risk_score"] > median_risk, "High",
                                 np.where(sup["risk_score"] > low_cut, "Medium", "Low"))

    def segment(r):
        big = r.spend >= median_spend and r.spend > 0
        if r.risk_score > median_risk:
            return "Tactical" if big else "At Risk"
        return "Strategic" if big else "Core"

    sup["segment"] = [segment(r) for r in sup.itertuples()]
    sup["recommendation"] = sup["segment"].map(RECOMMEND)
    n = len(sup)
    seg = sup["segment"].value_counts().reindex(SEGMENTS, fill_value=0)
    total_spend = sup["spend"].sum()
    weights = sup["spend"].where(sup["spend"] > 0, 1)
    otif_rate = (float(np.average(sup.loc[sup["otif"].notna(), "otif"], weights=weights[sup["otif"].notna()]))
                 if has_otif else None)

    y_key, y_label = ("otif", "On-Time Delivery Rate (%)") if has_otif else ("risk_score", "Risk score")
    groups = [{"name": s, "points": [{"x": float(r.lead_time or 0), "y": float(getattr(r, y_key) or 0), "label": r.name}
                                     for r in sup[sup["segment"] == s].itertuples()]} for s in SEGMENTS]

    def norm(series: pd.Series, invert: bool = False) -> pd.Series:
        s = series.astype(float).fillna(series.median() if series.notna().any() else 0)
        rng = s.max() - s.min()
        out = (s - s.min()) / rng if rng > 0 else pd.Series(0.5, index=s.index)
        return 1 - out if invert else out

    radar_feats = {"On-Time Delivery": norm(sup["otif"]) if has_otif else None,
                   "Short Lead Time": norm(sup["lead_time"], invert=True),
                   "Low Cost": norm(sup["avg_cost"], invert=True),
                   "Product Mix": norm(sup["products"]),
                   "Spend": norm(sup["spend"])}
    radar = []
    for axis, vals in radar_feats.items():
        if vals is None:
            continue
        row = {"axis": axis}
        for s in SEGMENTS:
            m = sup["segment"] == s
            if m.any():
                row[s] = round(float(vals[m].mean()), 3)
        radar.append(row)

    has_product_risk = sup["product_risk"].notna().any()
    sup["product_risk"] = sup["product_risk"].astype(float)
    rows = sup[["code", "name", "segment", "risk_level", "otif", "lead_time", "spend", "avg_cost", "products",
                "strategic_items", "critical_items", "product_risk", "categories", "single", "risk_score",
                "recommendation"]]
    risk_text = ("product supply risk (availability, few suppliers, non-standard, price swings) + lead time + lead-time variation"
                 if has_product_risk else "lead time + missed on-time deliveries + single-source exposure")
    if has_product_risk:
        notes = ["Strategic / Critical items: a product is high risk when its supply-risk index is above the median "
                 "product; Strategic if its spend is also above the median, otherwise Critical."]
    else:
        notes = [] if has_otif else ["Suppliers have no on-time delivery scores, so risk uses lead time and single sourcing only."]
    return page(
        input_={"title": "Supplier & purchase data (suppliers, supplier_products, products)",
                "scope": f"{n:,} suppliers · {int(sup['products'].sum()):,} supplier-product links",
                "columns": "Supplier, Product, Unit cost, Units sold, Lead time ± variation"
                           + (", Supply-risk factors" if has_product_risk else ", On-time score")},
        algorithm={"title": "Supplier Segmentation (Spend × Risk)",
                   "description": f"Risk score = {risk_text}. Against the median supplier: low risk + high spend → Strategic, low risk + low spend → Core, high risk + high spend → Tactical, high risk + low spend → At Risk."},
        output={"title": "supplier_segmentation_results",
                "description": "Segment, risk level, spend and recommended action per supplier."},
        kpis=[
            kpi("Total Suppliers", num(n), "Unique suppliers analyzed", "info", "users"),
            kpi("On-Time Delivery Rate", pct(otif_rate), "Spend-weighted average", "good", "truck") if has_otif else
            kpi("High-Risk Items", num(sup["strategic_items"].sum() + sup["critical_items"].sum()),
                f"{num(sup['strategic_items'].sum())} Strategic · {num(sup['critical_items'].sum())} Critical products",
                "warn", "alert") if has_product_risk else
            kpi("On-Time Delivery Rate", "—", "No on-time scores in the data", "neutral", "truck"),
            kpi("Avg. Lead Time", f"{sup['lead_time'].mean():.0f} days" if sup["lead_time"].notna().any() else "—",
                "Order to delivery", "info", "clock"),
            kpi("High Risk Suppliers", pct(seg["At Risk"] / n * 100, 0), f"{int(seg['At Risk']):,} suppliers",
                "bad" if seg["At Risk"] else "good", "alert"),
            kpi("Strategic Suppliers", pct(seg["Strategic"] / n * 100, 0),
                f"{int(seg['Strategic']):,} suppliers · {money(sup.loc[sup['segment'] == 'Strategic', 'spend'].sum())} spend",
                "info", "crown"),
        ],
        charts=[
            {"type": "scatter", "title": "Supplier Segmentation (Clusters)", "xLabel": "Average Lead Time (days)",
             "yLabel": y_label, "groups": groups, "colors": COLORS, "yFormat": "pct" if has_otif else "num"},
            {"type": "bar", "title": "Supplier Distribution by Segment",
             "data": [{"name": s, "value": float(v / n * 100)} for s, v in seg.items()], "valueFormat": "pct0",
             "colors": COLORS},
            {"type": "radar", "title": "Segment Characteristics (Normalized)", "data": radar,
             "series": [s for s in SEGMENTS if seg[s]], "colors": COLORS},
        ],
        table={
            "title": "Supplier Segmentation Results", "searchPlaceholder": "Search suppliers...",
            "columns": [
                col("code", "Supplier ID"), col("name", "Supplier Name"),
                col("segment", "Segment", "pill", pills={"Strategic": "good", "Core": "info", "Tactical": "warn", "At Risk": "bad"}),
                col("risk_level", "Risk Level", "pill", pills={"Low": "good", "Medium": "warn", "High": "bad"}),
                col("otif", "On-Time Delivery", "pct"), col("lead_time", "Lead Time (days)", "num"),
                col("spend", "Spend", "money"), col("avg_cost", "Avg. Cost", "money"),
                col("products", "Products", "int"),
                col("strategic_items", "Strategic Items", "int", hidden=not has_product_risk),
                col("critical_items", "Critical Items", "int", hidden=not has_product_risk),
                col("product_risk", "Supply Risk Index", "num2", hidden=True),
                col("categories", "Product Categories", "int", hidden=True),
                col("single", "Single-Source %", "pct", hidden=True), col("risk_score", "Risk Score", "num", hidden=True),
                col("recommendation", "Recommendation", "trend",
                    trends={"Increase volume": "up", "Maintain": "ok", "Negotiate cost": "right", "Find alternative": "down"}),
            ],
            "filters": ["segment", "risk_level", "recommendation"],
            "sort": {"key": "spend", "dir": "desc"},
            "rows": rows.to_dict("records"),
        },
        notes=notes,
    )
