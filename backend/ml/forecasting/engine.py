import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
from sqlalchemy.orm import Session
from backend.app.models.models import SalesHistory, Product, Warehouse, ProductForecast
from backend.ml.forecasting.daily_model import build_daily_series, fit, predict, backtest, DOW_NAMES

MODEL_NAME = "Exponential Smoothing + Day-of-Week Seasonality / Croston"

# In-memory fast cache to ensure <2ms response times during live retail demos
FORECAST_CACHE: Dict[str, Dict[str, Any]] = {}
CACHE_TTL = 300  # 5 minutes

class StatisticalForecastEngine:
    def __init__(self, db: Session):
        self.db = db

    def generate_forecast(self, product_id: int, warehouse_id: Optional[int] = None, horizon_days: int = 30) -> Dict[str, Any]:
        cache_key = f"{product_id}_{warehouse_id or 0}_{horizon_days}"
        now = time.time()
        
        # 1. Check in-memory demo cache
        if cache_key in FORECAST_CACHE:
            entry = FORECAST_CACHE[cache_key]
            if (now - entry.get("timestamp", 0)) < CACHE_TTL:
                return entry["data"]

        wh_id = warehouse_id or 0
        product = self.db.query(Product).filter(Product.id == product_id).first() if product_id else None
        if product_id and not product:
            raise ValueError(f"Product {product_id} not found")
        if not product:
            return {
                "product_id": product_id,
                "sku": None,
                "product_name": None,
                "warehouse_id": wh_id,
                "warehouse_name": None,
                "horizon_days": horizon_days,
                "total_forecasted_demand": None,
                "confidence_interval_pct": 95.0,
                "mae": None,
                "rmse": None,
                "accuracy_pct": None,
                "forecast_data": [],
                "historical_points": [],
                "model_name": MODEL_NAME
            }

        warehouse_name = "All Warehouses"
        if warehouse_id:
            wh = self.db.query(Warehouse).filter(Warehouse.id == warehouse_id).first()
            if wh:
                warehouse_name = wh.name

        today = datetime.utcnow().date()

        stored = self.db.query(ProductForecast).filter(
            ProductForecast.product_id == product_id,
            ProductForecast.warehouse_id == wh_id,
            ProductForecast.horizon_days == horizon_days
        ).first()

        # 3. Train on the product's real daily sales and forecast forward
        query = self.db.query(SalesHistory.date, SalesHistory.quantity_sold).filter(SalesHistory.product_id == product_id)
        if warehouse_id:
            query = query.filter(SalesHistory.warehouse_id == warehouse_id)
        series = build_daily_series(query.all())

        if not series:
            # No sales rows yet: nothing to learn from, so no forecast is made.
            return {
                "product_id": product.id,
                "sku": product.sku,
                "product_name": product.name,
                "warehouse_id": wh_id,
                "warehouse_name": warehouse_name,
                "horizon_days": horizon_days,
                "total_forecasted_demand": None,
                "confidence_interval_pct": 95.0,
                "mae": None,
                "rmse": None,
                "accuracy_pct": None,
                "forecast_data": [],
                "historical_points": [],
                "model_name": MODEL_NAME,
                "database_info": {
                    "is_connected": True,
                    "source": "Internal database (sales_history)",
                    "product_sku": product.sku,
                    "sales_records_used": 0,
                    "fallback_used": False
                },
                "calculation_trace": {
                    "model": MODEL_NAME,
                    "historical_days_evaluated": 0,
                    "data_source_tables": "sales_history (date, quantity_sold)",
                    "explanation": "No sales history for this product yet, so no forecast can be calculated."
                }
            }

        model = fit(series)
        bt = backtest(series)
        data_note = (
            f"Learned from {model['days_used']} days of real sales "
            f"({series[0]['date']} to {series[-1]['date']}, {round(model['total_units'])} units sold)."
        )

        forecast_points = predict(model, today + timedelta(days=1), horizon_days)
        total_demand = sum(p["forecasted_demand"] for p in forecast_points)
        historical_points = [
            {"date": p["date"].strftime("%Y-%m-%d"), "actual_demand": round(p["qty"], 1)}
            for p in series[-14:]
        ]

        mae = bt["mae"] if bt else None
        rmse = bt["rmse"] if bt else None
        accuracy_pct = bt["accuracy_pct"] if bt else None
        model_name = MODEL_NAME
        busiest = max(range(7), key=lambda i: model["dow_factors"][i])
        if model.get("method") == "croston":
            pattern_note = (
                f"This product sells on only {round((1 - model['zero_day_share']) * 100)}% of days, so we use Croston's method: "
                f"smoothed sale size / smoothed days between sales = about {round(model['level'], 1)} units/day on average."
            )
        else:
            pattern_note = (
                f"Typical day now is about {round(model['level'], 1)} units; "
                f"{DOW_NAMES[busiest]} is the busiest weekday (x{round(model['dow_factors'][busiest], 2)})."
            )

        result = {
            "product_id": product.id,
            "sku": product.sku,
            "product_name": product.name,
            "warehouse_id": wh_id,
            "warehouse_name": warehouse_name,
            "horizon_days": horizon_days,
            "total_forecasted_demand": round(total_demand, 1),
            "confidence_interval_pct": 95.0,
            "mae": mae,
            "rmse": rmse,
            "accuracy_pct": accuracy_pct,
            "forecast_data": forecast_points,
            "historical_points": historical_points,
            "model_name": model_name,
            "database_info": {
                "is_connected": True,
                "source": "Internal database (sales_history)",
                "product_sku": product.sku,
                "sales_records_used": model["days_used"],
                "fallback_used": False
            },
            "calculation_trace": {
                "model": model_name,
                "historical_days_evaluated": model["days_used"],
                "daily_mean_demand": round(model["overall_mean"], 2),
                "smoothed_level": round(model["level"], 2),
                "daily_std_dev": round(model["std"], 2),
                "day_of_week_factors": {DOW_NAMES[i]: round(f, 2) for i, f in enumerate(model["dow_factors"])},
                "backtest": bt,
                "method": model.get("method"),
                "formula": ("Croston/SBA: daily rate = 0.85 x smoothed sale size / smoothed days between sales"
                            if model.get("method") == "croston" else
                            "forecast(day) = smoothed level x day-of-week factor; level_t = 0.3 x demand_t + 0.7 x level_(t-1)"),
                "confidence_interval_formula": "forecast +/- 1.96 x std of past errors (95% band)",
                "data_source_tables": "sales_history (date, quantity_sold), products (sku, name)",
                "explanation": (
                    f"{data_note} {pattern_note} "
                    + (f"When we hid the last {bt['holdout_days']} days and predicted their total, we were {accuracy_pct}% accurate." if accuracy_pct is not None
                       else "Not enough history yet (need 21+ days) to measure accuracy.")
                )
            }
        }

        # 4. Persist in PostgreSQL product_forecasts table
        try:
            if stored:
                stored.total_forecasted_demand = round(total_demand, 1)
                stored.confidence_interval_pct = 95.0
                stored.mae = mae
                stored.rmse = rmse
                stored.forecast_data = forecast_points
                stored.historical_points = historical_points
                stored.model_name = model_name
                stored.updated_at = datetime.utcnow()
            else:
                new_fc = ProductForecast(
                    product_id=product.id,
                    warehouse_id=wh_id,
                    horizon_days=horizon_days,
                    total_forecasted_demand=round(total_demand, 1),
                    confidence_interval_pct=95.0,
                    mae=mae,
                    rmse=rmse,
                    forecast_data=forecast_points,
                    historical_points=historical_points,
                    model_name=model_name,
                    updated_at=datetime.utcnow()
                )
                self.db.add(new_fc)
            self.db.commit()
        except Exception as e:
            self.db.rollback()

        # Cache in memory
        FORECAST_CACHE[cache_key] = {"timestamp": now, "data": result}
        return result
