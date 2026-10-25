"""1. Demand Forecasting: per-product weekly series, model tournament on a hold-out, 12-week forecast."""
from typing import Callable, Dict, Optional

import numpy as np
import pandas as pd

from ._common import Data, NeedsData, col, date_range_text, demand_class, kpi, money, num, page, pct, short

HORIZON = 12
MAX_HOLDOUT = 12


def _naive(y, h):
    return np.full(h, y[-1])


def _ma(k):
    def f(y, h):
        return np.full(h, y[-k:].mean()) if len(y) >= k else None
    return f


def _ses(y, h, a=0.3):
    level = y[0]
    for v in y[1:]:
        level = a * v + (1 - a) * level
    return np.full(h, level)


def _croston(y, h, a=0.1):
    nz = np.flatnonzero(y)
    if len(nz) == 0:
        return np.zeros(h)
    size, interval, last = y[nz[0]], nz[0] + 1.0, nz[0]
    for i in nz[1:]:
        size = a * y[i] + (1 - a) * size
        interval = a * (i - last) + (1 - a) * interval
        last = i
    return np.full(h, size / interval)


def _seasonal(y, h):
    if len(y) < 52:
        return None
    idx = len(y) - 52 + np.arange(h)
    return y[idx]


def _trend(y, h):
    tail = y[-26:]
    if len(tail) < 8:
        return None
    slope, intercept = np.polyfit(np.arange(len(tail)), tail, 1)
    return np.clip(intercept + slope * (len(tail) + np.arange(h)), 0, None)


MODELS: Dict[str, Callable] = {
    "Naive": _naive, "Moving Avg (4w)": _ma(4), "Moving Avg (8w)": _ma(8), "Exp. Smoothing": _ses,
    "Croston": _croston, "Seasonal Naive": _seasonal, "Linear Trend": _trend,
}


def _week_start(d: pd.Series) -> pd.Series:
    return (d - pd.to_timedelta(d.dt.weekday, unit="D")).dt.normalize()


def compute(d: Data) -> Dict:
    s = d.sales
    if s.empty:
        raise NeedsData("sales history")
    p = d.product_costs().set_index("product_id")

    s = s.assign(week=_week_start(s["date"]))
    weeks = pd.date_range(s["week"].min(), s["week"].max(), freq="7D")
    if len(weeks) > 4 and s["date"].max().weekday() < 6:
        weeks = weeks[:-1]  # last week is incomplete: leave it out so it doesn't look like a sales drop
    mat = (s.pivot_table(index="product_id", columns="week", values="qty", aggfunc="sum", fill_value=0)
           .reindex(columns=weeks, fill_value=0))

    model_err = {m: [0.0, 0.0] for m in MODELS}  # abs error, actual units (products every model could score)
    rows, histories = [], {}
    total_err = total_act = 0.0
    tested = 0
    for pid, values in mat.iterrows():
        full = values.to_numpy(dtype=float)
        nz = np.flatnonzero(full)
        if len(nz) == 0:
            continue
        y = full[nz[0]:]
        hold = min(MAX_HOLDOUT, len(y) // 3)
        scores: Dict[str, float] = {}
        preds: Dict[str, np.ndarray] = {}
        if hold >= 2 and len(y) - hold >= 4:
            train, test = y[:-hold], y[-hold:]
            for name, fn in MODELS.items():
                f = fn(train, hold)
                if f is None:
                    continue
                scores[name] = float(np.abs(f - test).mean())
                preds[name] = f
        if scores:
            best = min(scores, key=scores.get)
            actual = test.sum()
            err = np.abs(preds[best] - test).sum()
            acc = max(0.0, 100 - err / actual * 100) if actual > 0 else None
            if actual > 0:
                total_err += err
                total_act += actual
                tested += 1
                for name, f in preds.items():
                    model_err[name][0] += np.abs(f - test).sum()
                    model_err[name][1] += actual
        else:
            best, acc, hold, test = "Moving Avg (4w)" if len(y) >= 4 else "Naive", None, 0, None
        fc = MODELS[best](y, HORIZON)
        if fc is None:
            fc = _naive(y, HORIZON)
        fc = np.clip(fc, 0, None)
        units = float(fc.sum())
        last12, prev12 = y[-12:].sum(), y[-24:-12].sum() if len(y) >= 24 else 0.0
        if prev12 > 0:
            change = (last12 - prev12) / prev12
            trend = "Growing" if change > 0.10 else "Declining" if change < -0.10 else "Stable"
        else:
            trend = "Growing" if last12 > 0 and len(y) >= 24 else "Stable"
        info = p.loc[pid] if pid in p.index else None
        price = float(info["avg_price"]) if info is not None else 0.0
        rows.append({
            "sku": info["sku"] if info is not None else str(pid),
            "product": info["name"] if info is not None else f"Product {pid}",
            "category": info["category"] if info is not None else "General",
            "demand_type": demand_class(y),
            "model": best,
            "avg_weekly": float(y.mean()),
            "last_12w": float(last12),
            "forecast_units": round(units),
            "forecast_revenue": units * price,
            "accuracy": acc,
            "trend": trend,
        })
        histories[pid] = (y, fc, best, hold, preds.get(best), scores.get(best))

    if not rows:
        raise NeedsData("sales history")
    df = pd.DataFrame(rows)
    avg_acc = max(0.0, 100 - total_err / total_act * 100) if total_act else None
    wins = df["model"].value_counts()
    top_model = wins.index[0]
    growing = int((df["trend"] == "Growing").sum())

    # Forecast vs actual for the 10 largest products: last 26 weeks, back-test fit, next 12 weeks.
    top_ids = (pd.Series({pid: h[1].sum() for pid, h in histories.items()}).sort_values(ascending=False).head(10).index)
    sku_by_id = p["sku"].to_dict()
    name_by_id = p["name"].to_dict()
    variants = []
    week_labels = list(mat.columns)
    for pid in top_ids:
        y, fc, best, hold, pred, mae = histories[pid]
        n_hist = min(26, len(y))
        start = len(week_labels) - n_hist
        pts = []
        for i in range(n_hist):
            idx = len(y) - n_hist + i
            point = {"label": f"{week_labels[start + i]:%d %b}", "actual": float(y[idx])}
            if pred is not None and idx >= len(y) - hold:
                point["forecast"] = float(pred[idx - (len(y) - hold)])
            pts.append(point)
        band = 1.28 * (mae or float(np.std(y[-12:])))
        last = week_labels[-1]
        for i, v in enumerate(fc):
            wk = last + pd.Timedelta(days=7 * (i + 1))
            pts.append({"label": f"{wk:%d %b}", "forecast": float(v),
                        "upper": float(v + band), "lower": float(max(0.0, v - band))})
        variants.append({"label": f"{sku_by_id.get(pid, pid)} · {short(name_by_id.get(pid, ''), 30)}", "data": pts,
                         "split": f"{last:%d %b}"})

    model_acc = sorted(
        ({"name": m, "value": max(0.0, 100 - e / a * 100)} for m, (e, a) in model_err.items() if a > 0),
        key=lambda r: -r["value"])[:5]
    top10 = df.nlargest(10, "forecast_units")

    n_rows = len(d.sales)
    return page(
        input_={"title": "Sales history (sales_history)",
                "scope": f"All warehouses · {n_rows:,} rows · {len(weeks)} weeks",
                "columns": "Product, Date, Quantity sold, Unit price"},
        algorithm={"title": "Model tournament: " + ", ".join(list(MODELS)[:4]) + " + 3 more",
                   "description": f"Each product's last weeks are hidden, every model predicts them, the lowest error (MAE) wins and forecasts the next {HORIZON} weeks."},
        output={"title": "demand_forecast_results",
                "description": f"{HORIZON}-week forecast per product with winning model, accuracy and trend ({len(df):,} rows)."},
        kpis=[
            kpi("Total Products Forecasted", num(len(df)), f"Products with {HORIZON}-week forecast", "info", "box"),
            kpi("Total Forecast Volume", num(df["forecast_units"].sum()), f"Units (next {HORIZON} weeks) · {money(df['forecast_revenue'].sum())}", "good", "chart"),
            kpi("Average Forecast Accuracy", pct(avg_acc), f"Back-tested on {tested:,} products", "info" if (avg_acc or 0) >= 60 else "warn", "target"),
            kpi("Top Performing Model", top_model, f"Won for {int(wins.iloc[0]):,} products", "neutral", "model"),
            kpi("High Demand Products", num(growing), "Last 12 weeks >10% above the 12 before", "good" if growing else "neutral", "trending",
                "up" if growing else None),
        ],
        charts=[
            {"type": "line", "title": "Forecast vs Actual", "subtitle": "Last 26 weeks + back-test fit + next 12 weeks",
             "series": [{"key": "actual", "label": "Actual", "color": "#3b82f6"},
                        {"key": "forecast", "label": "Forecast", "color": "#8b5cf6"},
                        {"key": "upper", "label": "Upper Bound", "color": "#c4b5fd", "dashed": True},
                        {"key": "lower", "label": "Lower Bound", "color": "#c4b5fd", "dashed": True}],
             "variants": variants, "valueFormat": "num"},
            {"type": "bar", "title": "Model Accuracy Comparison", "subtitle": "Accuracy on the hidden weeks, all products",
             "data": model_acc, "valueFormat": "pct", "multicolor": True},
            {"type": "hbar", "title": f"Top 10 Products by Forecast Volume",
             "data": [{"name": r.sku, "label": r.product, "value": r.forecast_units} for r in top10.itertuples()],
             "valueFormat": "num"},
        ],
        table={
            "title": "Forecast Results", "searchPlaceholder": "Search products...",
            "columns": [
                col("sku", "Product ID"), col("product", "Product Name"), col("category", "Category"),
                col("demand_type", "Demand Type", "pill", pills={"Smooth": "good", "Erratic": "warn", "Intermittent": "info", "Lumpy": "bad"}),
                col("model", "Model"),
                col("avg_weekly", "Avg Weekly Units", "num"),
                col("last_12w", "Last 12w Sold", "int", hidden=True),
                col("forecast_units", f"Forecast ({HORIZON}w)", "int"),
                col("forecast_revenue", "Forecast Revenue", "money"),
                col("accuracy", "Accuracy", "pct"),
                col("trend", "Trend", "trend"),
            ],
            "filters": ["category", "model", "demand_type", "trend"],
            "sort": {"key": "forecast_units", "dir": "desc"},
            "rows": df.to_dict("records"),
        },
        notes=[f"Sales data covers {date_range_text(d.sales['date'])}."],
    )
