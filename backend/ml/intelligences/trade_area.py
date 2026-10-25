"""9. Trade Area: store performance vs Huff-model potential and a location score per store."""
from typing import Dict

import numpy as np
import pandas as pd

from ._common import Data, NeedsData, col, kpi, money, num, page, pct

PERIOD_DAYS = 90


def _minmax(s: pd.Series) -> pd.Series:
    s = s.astype(float).fillna(0)
    rng = s.max() - s.min()
    return (s - s.min()) / rng if rng > 0 else pd.Series(0.5, index=s.index)


DISTANCE_DECAY = 2.0
STORE_COLORS = ["#3b82f6", "#a78bfa", "#10b981", "#f59e0b", "#ef4444"]


def compute_huff(d: Data) -> Dict:
    """Huff gravity model over the trade-area census, store attributes and distance matrix."""
    ta = d.trade_areas.set_index("code")
    st = d.trade_area_stores.set_index("code")
    dist = d.trade_area_distances.pivot_table(index="trade_area_code", columns="store_code", values="distance")
    dist = dist.reindex(index=ta.index, columns=st.index)
    attract = st["attractiveness"].fillna(st["size_sqft"]).astype(float)
    pull = attract / dist.clip(lower=0.1) ** DISTANCE_DECAY
    share = pull.div(pull.sum(axis=1), axis=0)
    potential = ta["market_potential"].astype(float).fillna(0)
    capture = share.mul(potential, axis=0)
    names = st["name"].to_dict()
    total = potential.sum()
    store_capture = capture.sum().sort_values(ascending=False)

    # Actual revenue per trade area: sales of the warehouse named after the area's country.
    actual = pd.Series(0.0, index=ta.index)
    if not d.sales.empty and not d.warehouses.empty:
        by_wh = d.sales.groupby("warehouse_id")["revenue"].sum()
        wh = d.warehouses.assign(revenue=lambda x: x["warehouse_id"].map(by_wh).fillna(0))
        rev_by_country = wh.groupby("name")["revenue"].sum()
        actual = ta["country"].map(rev_by_country).fillna(0.0)

    rows = pd.DataFrame({"code": ta.index, "country": ta["country"].values, "potential": potential.values,
                         "growth": (ta["growth_rate"].astype(float) * 100).values,
                         "competition": ta["competition_index"].astype(float).values,
                         "population": ta["population"].values, "actual": actual.values,
                         "winner": share.idxmax(axis=1).map(names).values})
    for code in st.index:
        rows[f"dist_{code}"] = dist[code].values
        rows[f"share_{code}"] = (share[code] * 100).values
        rows[f"cap_{code}"] = capture[code].values

    top_areas = rows.nlargest(10, "potential")
    share_chart = [{"name": r["country"], **{names[c]: float(r[f"share_{c}"]) for c in st.index}}
                   for _, r in top_areas.iterrows()]
    groups = [{"name": names[c], "points": [{"x": float(r.potential), "y": float(max(r.actual, 1)), "label": r.country}
                                            for r in rows[rows["winner"] == names[c]].itertuples() if r.potential > 0]}
              for c in st.index]
    colors = {names[c]: STORE_COLORS[i % len(STORE_COLORS)] for i, c in enumerate(st.index)}
    store_kpis = [kpi(f"{names[c]} Capture", money(v), f"{v / total * 100:.0f}% of market potential" if total else "",
                      "good" if i == 0 else "info" if i == 1 else "neutral", "store")
                  for i, (c, v) in enumerate(store_capture.head(3).items())]
    weakest = store_capture.index[-1]
    return page(
        input_={"title": "Trade-area census, stores & distances (trade_areas, trade_area_stores, trade_area_distances)",
                "scope": f"{len(ta):,} trade areas · {len(st):,} stores · {int(dist.notna().sum().sum()):,} distances",
                "columns": "Trade area, Country, Market potential, Store attractiveness, Distance, Actual revenue"},
        algorithm={"title": "Huff Gravity Model",
                   "description": f"Store pull on an area = attractiveness ÷ distance^{DISTANCE_DECAY:g}; share = pull ÷ sum of all stores' pull; expected capture = share × market potential."},
        output={"title": "trade_area_results",
                "description": "Choice probability and expected capture of every store in every trade area."},
        kpis=[kpi("Trade Areas Analyzed", num(len(ta)), f"{len(st)} competing stores", "info", "target"),
              kpi("Total Market Potential", money(total), "Spend available across all areas", "good", "chart"),
              *store_kpis],
        charts=[
            {"type": "bar", "title": "Store Share by Trade Area", "subtitle": "Top 10 areas by market potential",
             "data": share_chart, "valueFormat": "pct0", "stacked": True,
             "series": [{"key": names[c], "label": names[c], "color": colors[names[c]]} for c in st.index]},
            {"type": "bar", "title": "Expected Capture by Store", "subtitle": "Share × market potential, all areas",
             "data": [{"name": names[c], "value": float(v)} for c, v in store_capture.items()], "valueFormat": "money",
             "colors": colors},
            {"type": "scatter", "title": "Market Potential vs Actual Revenue", "xLabel": "Market potential",
             "yLabel": "Actual revenue", "xLog": True, "yLog": True, "groups": groups, "colors": colors,
             "xFormat": "money", "yFormat": "money"},
        ],
        table={
            "title": "Trade Area Results", "searchPlaceholder": "Search trade areas...",
            "columns": [
                col("code", "Area"), col("country", "Country"), col("potential", "Market Potential", "money"),
                *[col(f"dist_{c}", f"Distance {names[c]}", "num", hidden=True) for c in st.index],
                *[col(f"share_{c}", f"Share {names[c]}", "pct") for c in st.index],
                *[col(f"cap_{c}", f"Capture {names[c]}", "money", hidden=True) for c in st.index],
                col("winner", "Most Likely Store", "pill", pills={names[c]: ["info", "purple", "good", "warn"][i % 4]
                                                                 for i, c in enumerate(st.index)}),
                col("actual", "Actual Revenue", "money"),
                col("growth", "Growth Rate", "pct", hidden=True), col("competition", "Competition Index", "num2", hidden=True),
                col("population", "Population", "int", hidden=True),
            ],
            "filters": ["winner"],
            "sort": {"key": "potential", "dir": "desc"},
            "rows": rows.to_dict("records"),
        },
        notes=[f"{names[store_capture.index[0]]} captures the most because of its distance and attractiveness across the "
               f"largest markets; {names[weakest]} captures the least, so review its location.",
               "Census, store attributes and distances come from the trade-area input file; treat them as a model, "
               "not as observed visits."],
    )


def _has_trade_area_inputs(d: Data) -> bool:
    try:
        return not (d.trade_areas.empty or d.trade_area_stores.empty or d.trade_area_distances.empty)
    except Exception:  # tables not created yet on this database
        return False


def compute(d: Data) -> Dict:
    if _has_trade_area_inputs(d):
        return compute_huff(d)
    s = d.sales
    wh = d.warehouses
    if s.empty or wh.empty:
        raise NeedsData("sales history and warehouses / stores")
    end = s["date"].max()
    cur = s[s["date"] > end - pd.Timedelta(days=PERIOD_DAYS)]
    prev = s[(s["date"] <= end - pd.Timedelta(days=PERIOD_DAYS)) & (s["date"] > end - pd.Timedelta(days=2 * PERIOD_DAYS))]

    st = wh.set_index("warehouse_id")
    st["sales"] = cur.groupby("warehouse_id")["revenue"].sum()
    st["prev_sales"] = prev.groupby("warehouse_id")["revenue"].sum()
    st["products"] = cur.groupby("warehouse_id")["product_id"].nunique()
    st["units"] = cur.groupby("warehouse_id")["qty"].sum()
    o = d.orders
    if not o.empty and o["warehouse_id"].notna().any():
        oc = o[o["order_date"] > end - pd.Timedelta(days=PERIOD_DAYS)]
        st["customers"] = oc.groupby("warehouse_id")["customer_id"].nunique()
    else:
        st["customers"] = np.nan
    st[["sales", "products", "units"]] = st[["sales", "products", "units"]].fillna(0)
    st = st[(st["sales"] > 0) | (st["prev_sales"].fillna(0) > 0)]
    if st.empty:
        raise NeedsData("recent sales by warehouse / store")

    st["size"] = st["capacity_sqft"].fillna(st["capacity_sqft"].median()).fillna(50000).clip(lower=1)
    st["growth"] = np.where(st["prev_sales"].fillna(0) > 0, (st["sales"] / st["prev_sales"] - 1) * 100, np.nan)
    # Huff: attractiveness = size × assortment breadth; with no distances every store competes for the same market.
    attract = st["size"] * st["products"].clip(lower=1)
    st["huff_share"] = attract / attract.sum() * 100
    total = st["sales"].sum()
    st["potential"] = total * st["huff_share"] / 100
    st["sales_share"] = st["sales"] / total * 100 if total else 0
    st["per_sqft"] = st["sales"] / st["size"]
    st["score"] = (100 * (0.4 * _minmax(st["sales"]) + 0.3 * _minmax(st["growth"].fillna(0)) +
                          0.3 * _minmax(st["per_sqft"]))).round()
    q66, q33 = st["size"].quantile(0.66), st["size"].quantile(0.33)
    st["store_type"] = np.where(st["size"] >= q66, "Flagship", np.where(st["size"] <= q33, "Express", "Standard"))
    if len(st) < 3:
        st["store_type"] = "Standard"

    def rec(r):
        if (r.growth if not np.isnan(r.growth) else 0) < -5:
            return "Monitor"
        if r.potential > r.sales * 1.05 or r.score >= 70:
            return "Expand"
        return "Maintain"

    st["recommendation"] = [rec(r) for r in st.itertuples()]
    n = len(st)
    high = int((st["score"] >= 70).sum())
    expand = int((st["recommendation"] == "Expand").sum())
    top = st.sort_values("sales", ascending=False)
    chart_rows = top.head(10)
    donut = [{"name": r.name, "value": float(r.sales)} for r in top.head(5).itertuples()]
    if n > 5:
        donut.append({"name": "Others", "value": float(top.iloc[5:]["sales"].sum())})
    growth_total = (st["sales"].sum() / st["prev_sales"].sum() - 1) * 100 if st["prev_sales"].sum() > 0 else None

    rows = st.reset_index(drop=True)[["code", "name", "location", "store_type", "size", "products", "customers", "sales",
                                      "growth", "sales_share", "huff_share", "potential", "per_sqft", "score",
                                      "recommendation"]]
    return page(
        input_={"title": "Store, sales & location data (warehouses, sales_history, orders)",
                "scope": f"{n:,} stores · last {PERIOD_DAYS} days vs previous {PERIOD_DAYS}",
                "columns": "Store, Location, Size (sq ft), Sales, Products carried, Customers"},
        algorithm={"title": "Trade Area Analysis (Huff Gravity Model + Scoring)",
                   "description": "Huff share = store attractiveness (size × assortment) ÷ all stores; potential = share × market sales; score = 40% sales + 30% growth + 30% sales per sq ft."},
        output={"title": "trade_area_results",
                "description": "Store potential, location score, market share and expansion recommendation."},
        kpis=[
            kpi("Total Stores Analyzed", num(n), "Across all locations", "info", "store"),
            kpi("High Potential Locations", num(high), "Location score ≥ 70", "bad" if high == 0 else "good", "target"),
            kpi("Avg. Store Sales", money(st["sales"].mean()),
                f"{pct(growth_total, signed=True)} vs previous {PERIOD_DAYS} days" if growth_total is not None else f"Last {PERIOD_DAYS} days",
                "good" if (growth_total or 0) >= 0 else "warn", "chart",
                ("up" if growth_total >= 0 else "down") if growth_total is not None else None),
            kpi("Avg. Customers per Store", num(st["customers"].mean()) if st["customers"].notna().any() else num(st["products"].mean()),
                "Unique customers, last 90 days" if st["customers"].notna().any() else "Products carried per store",
                "info", "users"),
            kpi("Expansion Opportunities", num(expand), "Stores below their Huff potential or high scoring", "warn", "bulb"),
        ],
        charts=[
            {"type": "combo", "title": "Trade Area Sales Performance",
             "data": [{"name": r.name, "bar": float(r.sales), "line": float(r.growth) if not np.isnan(r.growth) else None}
                      for r in chart_rows.itertuples()],
             "barLabel": "Store Sales", "lineLabel": "Growth %", "barFormat": "money", "lineFormat": "pct"},
            {"type": "hbar", "title": "Location Potential Score",
             "data": [{"name": r.name, "value": float(r.score)} for r in st.sort_values("score", ascending=False).head(10).itertuples()],
             "valueFormat": "int", "wideLabels": True},
            {"type": "donut", "title": "Market Share by Store", "centerValue": num(n), "centerLabel": "Stores",
             "data": donut, "valueFormat": "money", "showPercent": True},
        ],
        table={
            "title": "Trade Area Results", "searchPlaceholder": "Search locations...",
            "columns": [
                col("code", "Location ID"), col("name", "Store"), col("location", "Region"),
                col("store_type", "Store Type", "pill", pills={"Flagship": "info", "Standard": "neutral", "Express": "warn"}),
                col("size", "Size (sq ft)", "int", hidden=True), col("products", "Products", "int"),
                col("customers", "Customers", "int", hidden=True),
                col("sales", "Current Sales", "money"), col("growth", "Growth", "pct_signed"),
                col("sales_share", "Market Share", "pct", hidden=True), col("huff_share", "Huff Share", "pct", hidden=True),
                col("potential", "Potential Sales", "money"), col("per_sqft", "Sales / sq ft", "money", hidden=True),
                col("score", "Location Score", "int"),
                col("recommendation", "Recommendation", "trend", trends={"Expand": "up", "Maintain": "ok", "Monitor": "down"}),
            ],
            "filters": ["store_type", "recommendation", "location"],
            "sort": {"key": "sales", "dir": "desc"},
            "rows": rows.to_dict("records"),
        },
        notes=["No travel distances or census data are stored, so every store competes for the same market; "
               "the Huff share comes from store size × products carried."],
    )
