"""2. Inventory Planning (safety stock, reorder point, EOQ) and 3. Inventory Policy Simulation."""
import math
from typing import Dict

import numpy as np
import pandas as pd

from ._common import (HOLDING_RATE, ORDER_COST, Data, NeedsData, abc_class, col, kpi, money, num, page,
                      pct, short, z_score)

PLANNING_WINDOW_DAYS = 120
SERVICE_LEVEL = {"A": 0.95, "B": 0.90, "C": 0.85}
SIM_WINDOW_DAYS = 180
SIM_TOP_N = 25
REVIEW_DAYS = 7


def _daily_matrix(d: Data, window_days: int) -> pd.DataFrame:
    s = d.sales
    if s.empty:
        raise NeedsData("sales history")
    end = s["date"].max().normalize()
    start = end - pd.Timedelta(days=window_days - 1)
    w = s[s["date"] >= start].assign(day=lambda x: x["date"].dt.normalize())
    days = pd.date_range(start, end, freq="D")
    return (w.pivot_table(index="product_id", columns="day", values="qty", aggfunc="sum", fill_value=0)
            .reindex(columns=days, fill_value=0))


def planning_params(d: Data, window_days: int = PLANNING_WINDOW_DAYS) -> pd.DataFrame:
    """Per product: daily demand mean/sd, ABC class, service level, safety stock, reorder point, EOQ."""
    mat = _daily_matrix(d, window_days)
    p = d.product_costs().set_index("product_id")
    df = pd.DataFrame({"mean": mat.mean(axis=1), "sd": mat.std(axis=1, ddof=0), "units": mat.sum(axis=1)})
    df = df.join(p[["sku", "name", "category", "unit_cost", "avg_price", "lead_time_days", "lead_time_sd_days",
                    "ordering_cost", "holding_rate"]], how="left")
    df["unit_cost"] = df["unit_cost"].fillna(0.0)
    df["avg_price"] = df["avg_price"].fillna(0.0)
    df["lead_time_days"] = df["lead_time_days"].fillna(7).clip(lower=1)
    df["lead_time_sd_days"] = df["lead_time_sd_days"].fillna(0.0)
    df["ordering_cost"] = df["ordering_cost"].fillna(ORDER_COST)
    df["holding_rate"] = df["holding_rate"].fillna(HOLDING_RATE)
    df["revenue"] = df["units"] * df["avg_price"]
    df["abc"] = abc_class(df["revenue"])
    df["service_level"] = df["abc"].map(SERVICE_LEVEL)
    z = df["service_level"].map(z_score)
    lt = df["lead_time_days"]
    df["safety_stock_fixed"] = np.ceil(z * df["sd"] * np.sqrt(lt))
    # Late or early deliveries add risk: sd during lead time = sqrt(LT·sd_demand² + mean_demand²·sd_LT²)
    df["safety_stock"] = np.ceil(z * np.sqrt(lt * df["sd"] ** 2 + (df["mean"] * df["lead_time_sd_days"]) ** 2))
    df["reorder_point"] = np.ceil(df["mean"] * lt + df["safety_stock"])
    annual = df["mean"] * 365
    holding = (df["unit_cost"] * df["holding_rate"]).clip(lower=0.01)
    df["eoq"] = np.ceil(np.sqrt(2 * annual * df["ordering_cost"] / holding)).fillna(0)
    df["annual_demand"] = annual
    df["ss_investment"] = df["safety_stock"] * df["unit_cost"]
    orders_per_year = np.where(df["eoq"] > 0, annual / df["eoq"].replace(0, np.nan), 0)
    df["annual_cost"] = (np.nan_to_num(orders_per_year) * df["ordering_cost"]
                         + (df["eoq"] / 2 + df["safety_stock"]) * holding)
    df["order_every_weeks"] = np.where(annual > 0, df["eoq"] / annual * 52, np.nan)
    return df


def compute_planning(d: Data) -> Dict:
    df = planning_params(d)
    inv = d.inventory.set_index("product_id")["stock"] if not d.inventory.empty else pd.Series(dtype=float)
    has_stock = not inv.empty
    df["stock"] = df.index.map(inv).astype(float) if has_stock else np.nan
    if has_stock:
        df["stock"] = df["stock"].fillna(0)

    def status(r):
        if not has_stock:
            return "No stock data"
        if r.stock <= 0:
            return "No Stock"
        if r.stock <= r.reorder_point:
            return "Reorder"
        if r.stock > r.reorder_point + r.eoq:
            return "Overstocked"
        return "Optimal"

    df["status"] = [status(r) for r in df.itertuples()]
    max_level = df["reorder_point"] + df["eoq"]
    df["recommended_qty"] = np.where(df["status"].isin(["Reorder", "No Stock"]),
                                     np.ceil(max_level - df["stock"].fillna(0)), 0)
    df["inventory_value"] = df["stock"] * df["unit_cost"]
    df["ss_days"] = np.where(df["mean"] > 0, df["safety_stock"] / df["mean"], np.nan)

    n = len(df)
    ss_days = f"{df['ss_days'].mean():.0f} days" if df["ss_days"].notna().any() else "—"
    fixed_total, var_total = df["safety_stock_fixed"].sum(), df["safety_stock"].sum()
    uplift = (var_total / fixed_total - 1) * 100 if fixed_total else None

    def category_chart(series: pd.Series, title: str, subtitle: str, fmt: str) -> Dict:
        by_cat = series.groupby(df["category"]).sum().sort_values(ascending=False)
        shown = by_cat.head(6)
        if len(by_cat) > 6:
            shown = pd.concat([shown, pd.Series({"Other": by_cat.iloc[6:].sum()})])
        return {"type": "bar", "title": title, "subtitle": subtitle, "valueFormat": fmt,
                "data": [{"name": k, "value": float(v)} for k, v in shown.items()]}

    if has_stock:
        reorder = int(df["status"].isin(["Reorder", "No Stock"]).sum())
        at_risk = int((df["stock"] < df["safety_stock"]).sum())
        by_status = df["status"].value_counts()
        kpis = [
            kpi("Total SKUs Analyzed", num(n), "Products with inventory plan", "info", "box"),
            kpi("Total Inventory Value", money(df["inventory_value"].sum()), "Stock on hand × unit cost", "good", "chart"),
            kpi("Average Safety Stock", ss_days, "Buffer against stockouts", "info", "shield"),
            kpi("Reorder Opportunities", num(reorder), "Need attention" if reorder else "Nothing to reorder",
                "warn" if reorder else "good", "cart"),
            kpi("Stockout Risk Products", num(at_risk), f"{at_risk / n * 100:.1f}% of total SKUs (below safety stock)",
                "bad" if at_risk else "good", "alert"),
        ]
        first_chart = {"type": "donut", "title": "Inventory Level Distribution", "centerValue": num(n), "centerLabel": "SKUs",
                       "data": [{"name": k, "value": int(by_status.get(k, 0))}
                                for k in ["Overstocked", "Optimal", "Reorder", "No Stock"] if by_status.get(k, 0)],
                       "colors": {"Overstocked": "#ef4444", "Optimal": "#10b981", "Reorder": "#f59e0b", "No Stock": "#3b82f6"},
                       "valueFormat": "int", "showPercent": True}
        second_chart = category_chart(df["recommended_qty"], "Recommended Order Quantities", "Units to order now, by category", "num")
        top = df.nlargest(10, "inventory_value")
        third_chart = {"type": "hbar", "title": "Top 10 SKUs by Inventory Value", "valueFormat": "money",
                       "data": [{"name": r.sku, "label": r.name, "value": float(r.inventory_value)} for r in top.itertuples()]}
    else:
        abc_counts = df["abc"].value_counts().reindex(["A", "B", "C"], fill_value=0)
        kpis = [
            kpi("Total SKUs Analyzed", num(n), f"Sold in the last {PLANNING_WINDOW_DAYS} days", "info", "box"),
            kpi("Safety Stock Investment", money(df["ss_investment"].sum()), "Safety stock × unit cost", "good", "chart"),
            kpi("Average Safety Stock", ss_days, "Of average daily demand", "info", "shield"),
            kpi("Annual Ordering + Holding", money(df["annual_cost"].sum()), "At the EOQ order size", "warn", "cart"),
            kpi("Lead-Time Variability Uplift", pct(uplift, signed=True) if uplift is not None else "—",
                f"Safety stock {num(fixed_total)} → {num(var_total)} units when deliveries vary", "bad" if (uplift or 0) > 0 else "good",
                "alert", "up" if (uplift or 0) > 0 else None),
        ]
        first_chart = {"type": "donut", "title": "ABC Class Distribution", "centerValue": num(n), "centerLabel": "SKUs",
                       "data": [{"name": f"Class {k}", "value": int(v)} for k, v in abc_counts.items() if v],
                       "colors": {"Class A": "#10b981", "Class B": "#3b82f6", "Class C": "#94a3b8"},
                       "valueFormat": "int", "showPercent": True}
        second_chart = category_chart(df["ss_investment"], "Safety Stock Investment by Category", "Safety stock × unit cost", "money")
        top = df.nlargest(10, "ss_investment")
        third_chart = {"type": "hbar", "title": "Top 10 SKUs by Safety Stock Investment", "valueFormat": "money",
                       "data": [{"name": r.sku, "label": r.name, "value": float(r.ss_investment)} for r in top.itertuples()]}

    rows = df.reset_index().rename(columns={"name": "product"})
    rows = rows[["sku", "product", "category", "abc", "service_level", "mean", "lead_time_days", "lead_time_sd_days",
                 "stock", "safety_stock_fixed", "safety_stock", "reorder_point", "eoq", "order_every_weeks",
                 "recommended_qty", "ss_investment", "annual_cost", "status", "inventory_value"]]
    rows = rows.assign(service_level=rows["service_level"] * 100)
    stock_cols = [col("stock", "Current Stock", "int"), col("recommended_qty", "Recommended Qty", "int"),
                  col("status", "Stock Status", "trend",
                      trends={"Reorder": "down", "No Stock": "down", "Optimal": "ok", "Overstocked": "up"}),
                  col("inventory_value", "Inventory Value", "money")] if has_stock else []
    return page(
        input_={"title": "Sales & product planning data (sales_history, products, inventory)",
                "scope": f"Last {PLANNING_WINDOW_DAYS} days · {n:,} products",
                "columns": "Date, Quantity, Unit cost, Lead time ± variation, Ordering cost, Holding rate"
                           + (", Stock on hand" if has_stock else "")},
        algorithm={"title": "Safety Stock + Reorder Point + EOQ",
                   "description": "ABC class sets the service level; safety stock = z × √(lead time × demand sd² + demand² × lead-time sd²); reorder point = lead-time demand + safety stock; EOQ = √(2 × annual demand × order cost ÷ holding cost)."},
        output={"title": "inventory_planning_results",
                "description": "Safety stock, reorder point, order quantity and yearly cost per product"
                               + (", with stock status." if has_stock else ".")},
        kpis=kpis,
        charts=[first_chart, second_chart, third_chart],
        table={
            "title": "Inventory Planning Results", "searchPlaceholder": "Search products...",
            "columns": [
                col("sku", "Product ID"), col("product", "Product Name"), col("category", "Category"),
                col("abc", "ABC Class", "pill", pills={"A": "good", "B": "info", "C": "neutral"}),
                col("service_level", "Target Service", "pct", hidden=has_stock),
                col("mean", "Avg Daily Demand", "num", hidden=has_stock),
                col("lead_time_days", "Lead Time", "days"),
                col("lead_time_sd_days", "Lead Time ±", "num", hidden=True),
                col("safety_stock_fixed", "Safety Stock (fixed LT)", "int", hidden=True),
                col("safety_stock", "Safety Stock", "int"),
                col("reorder_point", "Reorder Point", "bold_int"),
                col("eoq", "EOQ", "int", hidden=has_stock),
                col("order_every_weeks", "Order Every (wks)", "num", hidden=True),
                *stock_cols,
                col("ss_investment", "Safety Stock $", "money", hidden=has_stock),
                col("annual_cost", "Yearly Order + Holding", "money", hidden=has_stock),
            ],
            "filters": ["category", "abc"] + (["status"] if has_stock else []),
            "sort": {"key": "inventory_value" if has_stock else "ss_investment", "dir": "desc"},
            "rows": rows.to_dict("records"),
        },
        notes=[] if has_stock else ["There is no stock-on-hand data, so the plan shows targets (safety stock, reorder point, order size) and their cost instead of current stock status."],
    )


# --- policy simulation ----------------------------------------------------------------------

POLICIES = {
    "min_q": "(s, Q) Min-Q",
    "min_max": "(s, S) Min-Max",
    "base_stock": "Base Stock",
    "periodic": "(R, S) Periodic",
    "hybrid": "(R, s, S) Hybrid",
}


def _simulate(demand: np.ndarray, policy: str, s: float, q: float, lt: int, review_target: float,
              base_target: float) -> Dict[str, float]:
    S = s + q
    on_hand = float(S)
    pipeline = []  # (arrival day, qty)
    served = lost = held = 0.0
    orders = stockout_days = 0
    for day, dem in enumerate(demand):
        arrived = sum(qty for t, qty in pipeline if t == day)
        pipeline = [(t, qty) for t, qty in pipeline if t != day]
        on_hand += arrived
        sold = min(on_hand, dem)
        served += sold
        if dem > sold:
            lost += dem - sold
            stockout_days += 1
        on_hand -= sold
        held += on_hand
        position = on_hand + sum(qty for _, qty in pipeline)
        review = day % REVIEW_DAYS == 0
        order = 0.0
        if policy == "min_q" and position <= s:
            order = q
        elif policy == "min_max" and position <= s:
            order = S - position
        elif policy == "base_stock" and position < base_target:
            order = base_target - position
        elif policy == "periodic" and review and position < review_target:
            order = review_target - position
        elif policy == "hybrid" and ((review and position <= s) or position <= s * 0.5):
            order = S - position
        if order > 0:
            orders += 1
            pipeline.append((day + lt, math.ceil(order)))
    total = float(demand.sum())
    return {"fill_rate": served / total * 100 if total else 100.0, "avg_stock": held / len(demand),
            "orders": orders, "lost": lost, "stockout_days": stockout_days}


def compute_policy(d: Data) -> Dict:
    params = planning_params(d, SIM_WINDOW_DAYS)
    mat = _daily_matrix(d, SIM_WINDOW_DAYS)
    top = params[params["mean"] > 0].nlargest(SIM_TOP_N, "revenue")
    if top.empty:
        raise NeedsData("sales history")
    days = mat.shape[1]
    year = 365 / days
    results, rows = [], []
    for pid, r in top.iterrows():
        demand = mat.loc[pid].to_numpy(dtype=float)
        lt = int(round(r.lead_time_days))
        z = z_score(r.service_level)
        s = max(1.0, r.reorder_point)
        q = max(1.0, r.eoq)
        review_target = math.ceil(r["mean"] * (REVIEW_DAYS + lt) + z * r["sd"] * math.sqrt(REVIEW_DAYS + lt))
        base_target = math.ceil(r["mean"] * (lt + 1) + r.safety_stock)
        margin = max(r.avg_price - r.unit_cost, r.avg_price * 0.2)
        per_policy = {}
        for key, label in POLICIES.items():
            out = _simulate(demand, key, s, q, lt, review_target, base_target)
            holding = out["avg_stock"] * r.unit_cost * r.holding_rate
            ordering = out["orders"] * r.ordering_cost * year
            shortage = out["lost"] * margin * year
            out.update(policy=label, holding=holding, ordering=ordering, shortage=shortage,
                       annual_cost=holding + ordering + shortage)
            per_policy[key] = out
            results.append({**out, "product_id": pid})
        target = r.service_level * 100
        meeting = {k: v for k, v in per_policy.items() if v["fill_rate"] >= target}
        best_key = (min(meeting, key=lambda k: meeting[k]["annual_cost"]) if meeting
                    else max(per_policy, key=lambda k: per_policy[k]["fill_rate"]))
        best = per_policy[best_key]
        worst_cost = max(v["annual_cost"] for v in per_policy.values())
        rows.append({
            "sku": r.sku, "product": r["name"], "category": r.category,
            "best_policy": best["policy"], "service_level": best["fill_rate"], "target_service": target,
            "annual_cost": best["annual_cost"], "stockouts": best["stockout_days"], "lost_units": best["lost"],
            "avg_stock": best["avg_stock"], "saving_vs_worst": worst_cost - best["annual_cost"],
            "reorder_point": s, "order_qty": q,
            **{f"cost_{k}": v["annual_cost"] for k, v in per_policy.items()},
        })
    res = pd.DataFrame(results)
    df = pd.DataFrame(rows)
    by_policy = res.groupby("policy").agg(fill=("fill_rate", "mean"), cost=("annual_cost", "sum"),
                                          stockouts=("stockout_days", "sum")).reindex(list(POLICIES.values()))
    wins = df["best_policy"].value_counts()
    best_policy = wins.index[0]
    best_cost = df["annual_cost"].sum()
    worst_total = by_policy["cost"].max()
    with_stockouts = int((df["stockouts"] > 0).sum())
    return page(
        input_={"title": "Daily demand + planning parameters",
                "scope": f"Top {len(df)} products by revenue · last {SIM_WINDOW_DAYS} days",
                "columns": "Daily quantity, Reorder point, EOQ, Lead time, Unit cost, Price"},
        algorithm={"title": "Compare 5 Reorder Policies",
                   "description": "(s, Q), (s, S), base stock, (R, S) and (R, s, S) are replayed day by day on real demand; each tracks fill rate, stockouts, holding, ordering and lost-margin cost."},
        output={"title": "inventory_policy_results",
                "description": "Service level, annual cost, stockouts and the recommended policy for each product."},
        kpis=[
            kpi("Policies Compared", str(len(POLICIES)), "Reorder policies", "info", "layers"),
            kpi("Best Policy", best_policy, f"Wins for {int(wins.iloc[0])} of {len(df)} products", "good", "trophy"),
            kpi("Total Annual Cost", money(best_cost),
                f"{(1 - best_cost / worst_total) * 100:.1f}% below the costliest policy" if worst_total else "",
                "good", "database", "down"),
            kpi("Average Service Level", pct(df["service_level"].mean()), "Fill rate with the best policy", "info", "shield"),
            kpi("Products with Stockouts", num(with_stockouts), f"{with_stockouts / len(df) * 100:.1f}% of simulated SKUs",
                "bad" if with_stockouts else "good", "alert"),
        ],
        charts=[
            {"type": "bar", "title": "Service Level Comparison", "subtitle": "Average fill rate per policy",
             "data": [{"name": k, "value": float(v)} for k, v in by_policy["fill"].items()], "valueFormat": "pct",
             "multicolor": True},
            {"type": "bar", "title": "Total Annual Cost Comparison", "subtitle": "Holding + ordering + lost margin",
             "data": [{"name": k, "value": float(v)} for k, v in by_policy["cost"].items()], "valueFormat": "money",
             "multicolor": True},
            {"type": "bar", "title": "Stockouts by Policy", "subtitle": "Days with lost sales, all products",
             "data": [{"name": k, "value": float(v)} for k, v in by_policy["stockouts"].items()], "valueFormat": "int",
             "multicolor": True},
        ],
        table={
            "title": "Policy Simulation Results", "searchPlaceholder": "Search products...",
            "columns": [
                col("sku", "Product ID"), col("product", "Product Name"), col("category", "Category"),
                col("best_policy", "Best Policy", "pill"),
                col("service_level", "Service Level", "pct"),
                col("target_service", "Target", "pct", hidden=True),
                col("annual_cost", "Annual Cost", "money"),
                col("stockouts", "Stockout Days", "int"),
                col("lost_units", "Lost Units", "int", hidden=True),
                col("avg_stock", "Avg Stock Held", "int"),
                col("saving_vs_worst", "Saving vs Worst", "money"),
                col("reorder_point", "Reorder Point", "int", hidden=True),
                col("order_qty", "Order Qty", "int", hidden=True),
                *[col(f"cost_{k}", f"Cost · {label}", "money", hidden=True) for k, label in POLICIES.items()],
            ],
            "filters": ["category", "best_policy"],
            "sort": {"key": "annual_cost", "dir": "desc"},
            "rows": df.to_dict("records"),
        },
        notes=["Each product's own ordering cost and yearly holding rate are used (defaults "
               f"{money(ORDER_COST)} per order and {HOLDING_RATE:.0%} when missing); lost sales cost the unit margin; "
               "costs are annualised from the simulated window."],
    )
