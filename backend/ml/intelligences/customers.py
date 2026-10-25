"""5. Customer Value: RFM scoring, segments and lifetime value per customer."""
from typing import Dict

import numpy as np
import pandas as pd

from ._common import Data, NeedsData, col, kpi, money, num, page, pct

SEGMENTS = ["Champions", "Loyal", "Potential", "At Risk", "Lost"]
STATUS = {"Champions": "Active", "Loyal": "Active", "Potential": "Growing", "At Risk": "At Risk", "Lost": "Lost"}
ACTION = {"Champions": "Upsell premium products", "Loyal": "Cross-sell & bundle offers",
          "Potential": "Increase purchase frequency", "At Risk": "Reactivation campaign", "Lost": "Win-back campaign"}


def _score(values: pd.Series) -> pd.Series:
    """1-5 quintile score by rank (works for any number of customers)."""
    return np.ceil(values.rank(method="average", pct=True) * 5).clip(1, 5).astype(int)


def _segment(r: int, f: int) -> str:
    if r >= 4 and f >= 4:
        return "Champions"
    if r >= 3 and f >= 3:
        return "Loyal"
    if r >= 3:
        return "Potential"
    if r == 1 and f <= 2:
        return "Lost"
    return "At Risk"


def compute(d: Data) -> Dict:
    o = d.orders
    o = o[o["customer_id"].notna() & o["order_date"].notna()]
    if o.empty:
        raise NeedsData("orders with customers")
    snapshot = o["order_date"].max().normalize() + pd.Timedelta(days=1)
    c = o.groupby("customer_id").agg(
        code=("customer_code", "first"), name=("customer_name", "first"),
        last=("order_date", "max"), first=("order_date", "min"),
        frequency=("order_id", "nunique"), monetary=("total_amount", "sum"))
    c["recency"] = (snapshot - c["last"]).dt.days
    c["r"] = _score(-c["recency"])
    c["f"] = _score(c["frequency"])
    c["m"] = _score(c["monetary"])
    c["segment"] = [_segment(r, f) for r, f in zip(c["r"], c["f"])]
    c["status"] = c["segment"].map(STATUS)
    c["opportunity"] = c["segment"].map(ACTION)
    c["aov"] = c["monetary"] / c["frequency"]
    c["ltv"] = c["monetary"]
    c["rfm"] = c["r"].astype(str) + "-" + c["f"].astype(str) + "-" + c["m"].astype(str)
    c["code"] = c["code"].fillna(c.index.to_series().astype(str))

    n = len(c)
    total = c["monetary"].sum()
    high = c[c["segment"].isin(["Champions", "Loyal"])]
    at_risk = c[c["segment"] == "At Risk"]
    seg_counts = c["segment"].value_counts().reindex(SEGMENTS, fill_value=0)
    top10 = c.nlargest(10, "ltv")

    pts = c.sample(min(n, 800), random_state=42) if n > 800 else c
    groups = [{"name": s, "points": [{"x": float(max(r.recency, 1)), "y": float(max(r.monetary, 0.01)), "label": str(r.code)}
                                     for r in pts[pts["segment"] == s].itertuples()]} for s in SEGMENTS]

    rows = c.reset_index(drop=True)[["code", "name", "segment", "recency", "frequency", "monetary", "aov", "rfm", "ltv",
                                     "status", "opportunity"]]
    return page(
        input_={"title": "Customer & order data (orders, customers)",
                "scope": f"{len(o):,} orders · {n:,} customers",
                "columns": "Customer ID, Order ID, Order date, Order total"},
        algorithm={"title": "RFM Segmentation + LTV",
                   "description": "Recency, Frequency and Monetary value are scored 1–5 by rank; R and F scores place each customer in a segment; LTV = total spend to date."},
        output={"title": "customer_value_results",
                "description": "Segment, RFM score, LTV, status and growth action per customer."},
        kpis=[
            kpi("Total Customers", num(n), "Unique customers analyzed", "info", "users"),
            kpi("Average LTV", money(c["ltv"].mean()), f"Avg order value {money(c['aov'].mean())}", "info", "chart"),
            kpi("High Value Customers", pct(len(high) / n * 100, 0), f"{len(high):,} Champions & Loyal", "good", "trophy"),
            kpi("Revenue from High Value", pct(high["monetary"].sum() / total * 100, 0) if total else "—",
                f"{money(high['monetary'].sum())} of {money(total)}", "good", "database"),
            kpi("At Risk Customers", pct(len(at_risk) / n * 100, 0), f"{len(at_risk):,} customers",
                "bad" if len(at_risk) else "good", "alert"),
        ],
        charts=[
            {"type": "scatter", "title": "Customer Segmentation (RFM)", "xLabel": "Recency (days)", "yLabel": "Monetary",
             "xLog": True, "yLog": True, "groups": groups, "yFormat": "money",
             "colors": {"Champions": "#3b82f6", "Loyal": "#10b981", "Potential": "#f59e0b", "At Risk": "#f97316", "Lost": "#ef4444"}},
            {"type": "bar", "title": "Customer Value Distribution", "subtitle": "Share of customers per segment",
             "data": [{"name": s, "value": float(v / n * 100)} for s, v in seg_counts.items()], "valueFormat": "pct0",
             "colors": {"Champions": "#3b82f6", "Loyal": "#10b981", "Potential": "#f59e0b", "At Risk": "#f97316", "Lost": "#ef4444"}},
            {"type": "hbar", "title": "Top 10 Customers by LTV",
             "data": [{"name": str(r.code), "label": r.name, "value": float(r.ltv)} for r in top10.itertuples()],
             "valueFormat": "money"},
        ],
        table={
            "title": "Customer Value Results", "searchPlaceholder": "Search customers...",
            "columns": [
                col("code", "Customer ID"), col("name", "Customer Name"),
                col("segment", "Segment", "pill", pills={"Champions": "info", "Loyal": "good", "Potential": "warn",
                                                         "At Risk": "orange", "Lost": "bad"}),
                col("recency", "Recency (days)", "int"), col("frequency", "Frequency", "int"),
                col("monetary", "Monetary", "money"), col("aov", "Avg Order", "money", hidden=True),
                col("rfm", "R-F-M", hidden=True),
                col("ltv", "LTV", "money"),
                col("status", "Status", "trend", trends={"Active": "up", "Growing": "ok", "At Risk": "down", "Lost": "down"}),
                col("opportunity", "Growth Opportunity"),
            ],
            "filters": ["segment", "status"],
            "sort": {"key": "ltv", "dir": "desc"},
            "rows": rows.to_dict("records"),
        },
        notes=[f"Recency is measured from {snapshot:%d %b %Y} (the day after the latest order)."],
    )
