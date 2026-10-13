"""Small, explainable daily demand model used by the forecast engine and the dashboard.

Smooth sellers: exponential smoothing of the de-seasonalised daily demand (the "level"),
multiplied by a day-of-week factor learned from the same history.
Intermittent sellers (sales on fewer than 70% of days): Croston's method with the
Syntetos-Boylan correction, which smooths "size of a sale" and "days between sales"
separately and forecasts their ratio as a flat daily rate.
Accuracy is measured by hiding the last `holdout` days, refitting on the rest and
comparing the predicted total for those days with what actually sold.
"""
from datetime import date, timedelta
from typing import Dict, Any, List, Optional
import math

ALPHA = 0.3
INTERMITTENT_ZERO_SHARE = 0.3
DOW_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def build_daily_series(rows: List[Any], max_days: int = 180) -> List[Dict[str, Any]]:
    """rows: iterable of (date/datetime, qty). Returns contiguous days (missing days = 0)."""
    totals: Dict[date, float] = {}
    for d, qty in rows:
        if d is None:
            continue
        day = d.date() if hasattr(d, "date") else d
        totals[day] = totals.get(day, 0.0) + float(qty or 0)
    if not totals:
        return []
    end = max(totals)
    start = max(min(totals), end - timedelta(days=max_days - 1))
    series = []
    cur = start
    while cur <= end:
        series.append({"date": cur, "qty": totals.get(cur, 0.0)})
        cur += timedelta(days=1)
    return series


def _croston_rate(values: List[float]) -> float:
    size = interval = None
    gap = 1
    for v in values:
        if v > 0:
            size = v if size is None else ALPHA * v + (1 - ALPHA) * size
            interval = gap if interval is None else ALPHA * gap + (1 - ALPHA) * interval
            gap = 1
        else:
            gap += 1
    if not size or not interval:
        return 0.0
    return (1 - ALPHA / 2) * size / interval


def fit(series: List[Dict[str, Any]]) -> Dict[str, Any]:
    values = [p["qty"] for p in series]
    overall_mean = sum(values) / len(values) if values else 0.0
    zero_share = (sum(1 for v in values if v <= 0) / len(values)) if values else 0.0
    intermittent = zero_share > INTERMITTENT_ZERO_SHARE

    dow_factors = [1.0] * 7
    if not intermittent and len(series) >= 14 and overall_mean > 0:
        sums = [0.0] * 7
        counts = [0] * 7
        for p in series:
            wd = p["date"].weekday()
            sums[wd] += p["qty"]
            counts[wd] += 1
        dow_factors = [
            (sums[i] / counts[i]) / overall_mean if counts[i] else 1.0
            for i in range(7)
        ]

    if intermittent:
        level = _croston_rate(values)
    else:
        level = None
        for p in series:
            factor = dow_factors[p["date"].weekday()] or 1.0
            deseason = p["qty"] / factor
            level = deseason if level is None else ALPHA * deseason + (1 - ALPHA) * level
        level = level or 0.0

    residuals = [p["qty"] - level * dow_factors[p["date"].weekday()] for p in series]
    std = math.sqrt(sum(r * r for r in residuals) / len(residuals)) if residuals else 0.0

    return {
        "method": "croston" if intermittent else "smoothing",
        "zero_day_share": round(zero_share, 2),
        "level": level,
        "dow_factors": dow_factors,
        "overall_mean": overall_mean,
        "std": std,
        "days_used": len(series),
        "total_units": sum(values),
    }


def predict(model: Dict[str, Any], start: date, horizon: int) -> List[Dict[str, Any]]:
    margin = 1.96 * model["std"]
    points = []
    for d in range(horizon):
        day = start + timedelta(days=d)
        val = max(0.0, model["level"] * model["dow_factors"][day.weekday()])
        points.append({
            "date": day.strftime("%Y-%m-%d"),
            "forecasted_demand": round(val, 1),
            "lower_bound": round(max(0.0, val - margin), 1),
            "upper_bound": round(val + margin, 1),
        })
    return points


def backtest(series: List[Dict[str, Any]], holdout: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """Hide the last `holdout` days, predict them from the earlier days, compare with reality.
    Defaults to 28 days when there is enough history (lumpy sellers make 7-day totals very noisy)."""
    if holdout is None:
        holdout = 28 if len(series) >= 84 else 7
    if len(series) < holdout + 14:
        return None
    train, test = series[:-holdout], series[-holdout:]
    model = fit(train)
    preds = predict(model, test[0]["date"], holdout)
    errors = [t["qty"] - p["forecasted_demand"] for t, p in zip(test, preds)]
    actual_total = sum(t["qty"] for t in test)
    predicted_total = sum(p["forecasted_demand"] for p in preds)
    total_err = abs(actual_total - predicted_total)
    error_pct = (total_err / actual_total * 100.0) if actual_total > 0 else None
    return {
        "holdout_days": holdout,
        "actual_units": round(actual_total, 1),
        "predicted_units": round(predicted_total, 1),
        "abs_error_units": round(total_err, 1),
        "mae": round(sum(abs(e) for e in errors) / holdout, 2),
        "rmse": round(math.sqrt(sum(e * e for e in errors) / holdout), 2),
        "error_pct": round(error_pct, 1) if error_pct is not None else None,
        "accuracy_pct": round(max(0.0, 100.0 - error_pct), 1) if error_pct is not None else None,
        "comparison": [
            {"date": t["date"].strftime("%Y-%m-%d"), "actual": round(t["qty"], 1), "predicted": p["forecasted_demand"]}
            for t, p in zip(test, preds)
        ],
    }
