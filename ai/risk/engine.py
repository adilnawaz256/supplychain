from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from backend.app.models.models import Inventory, Product, Warehouse, Supplier, SupplierProduct
from ai.inventory.optimization import InventoryOptimizer
from ai.forecasting.engine import StatisticalForecastEngine

class InventoryRiskEngine:
    def __init__(self, db: Session):
        self.db = db
        self.optimizer = InventoryOptimizer(db)
        self.forecaster = StatisticalForecastEngine(db)

    def evaluate_product_risk(self, product_id: int, warehouse_id: int) -> Dict[str, Any]:
        opt_metrics = self.optimizer.calculate_inventory_metrics(product_id, warehouse_id)
        forecast_res = self.forecaster.generate_forecast(product_id, warehouse_id, horizon_days=7)
        
        forecast_7d = forecast_res["total_forecasted_demand"]
        current_stock = opt_metrics["current_stock"]
        lead_time = opt_metrics["lead_time_days"]
        doi = opt_metrics["days_of_inventory"]
        safety_stock = opt_metrics["safety_stock_calculated"]
        rop = opt_metrics["reorder_point_calculated"]

        # Find primary supplier name
        sup_prod = self.db.query(SupplierProduct).filter(SupplierProduct.product_id == product_id).first()
        supplier_name = "Primary Vendor"
        if sup_prod:
            sup = self.db.query(Supplier).filter(Supplier.id == sup_prod.supplier_id).first()
            if sup:
                supplier_name = sup.name

        # Classification Logic
        # 1. CRITICAL: Stock < Safety Stock OR Days of Inventory < Lead Time
        if current_stock < safety_stock or doi < lead_time:
            risk_level = "CRITICAL"
            reason = (
                f"CRITICAL STOCKOUT RISK! Current stock ({current_stock}) is below safety stock threshold ({safety_stock}) "
                f"or days of inventory ({doi} days) is less than supplier lead time ({lead_time} days). "
                f"Forecast demand over next 7 days is {forecast_7d} units."
            )
        # 2. HIGH: Stock <= Reorder Point OR DOI <= Lead Time + 3
        elif current_stock <= rop or doi <= (lead_time + 3):
            risk_level = "HIGH"
            reason = (
                f"High stockout risk. Current stock ({current_stock}) is at or below reorder point ({rop}). "
                f"Lead time is {lead_time} days; expected stock depletion in {doi} days."
            )
        # 3. LOW (Excess): DOI > 60 days or Current Stock > ROP * 4
        elif doi > 60.0 or current_stock > (rop * 4):
            risk_level = "LOW"
            reason = (
                f"Excess stock / low risk. Current stock ({current_stock}) provides {doi} days of inventory. "
                f"Consider reallocating inventory to prevent high holding cost."
            )
        # 4. MEDIUM: Normal operating inventory
        else:
            risk_level = "MEDIUM"
            reason = f"Stable inventory level ({current_stock} units, {doi} days of supply). Operating within normal parameters."

        return {
            "product_id": opt_metrics["product_id"],
            "sku": opt_metrics["sku"],
            "product_name": opt_metrics["product_name"],
            "warehouse_id": opt_metrics["warehouse_id"],
            "warehouse_name": opt_metrics["warehouse_name"],
            "current_stock": current_stock,
            "allocated_stock": opt_metrics["allocated_stock"],
            "available_stock": opt_metrics["available_stock"],
            "avg_daily_demand": opt_metrics["avg_daily_demand"],
            "forecast_7d_demand": forecast_7d,
            "lead_time_days": lead_time,
            "safety_stock": safety_stock,
            "reorder_point": rop,
            "days_of_inventory": doi,
            "stockout_risk_level": risk_level,
            "reasoning": reason,
            "recommended_order_quantity": opt_metrics["recommended_order_quantity"],
            "supplier_name": supplier_name
        }

    def get_all_inventory_risks(self, warehouse_id: Optional[int] = None, risk_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        query = self.db.query(Inventory)
        if warehouse_id:
            query = query.filter(Inventory.warehouse_id == warehouse_id)

        inventory_items = query.all()
        results = []

        for inv in inventory_items:
            try:
                eval_res = self.evaluate_product_risk(inv.product_id, inv.warehouse_id)
                if risk_filter:
                    if eval_res["stockout_risk_level"] == risk_filter.upper():
                        results.append(eval_res)
                else:
                    results.append(eval_res)
            except Exception as e:
                continue

        # Sort by risk severity (CRITICAL > HIGH > MEDIUM > LOW)
        order_map = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        results.sort(key=lambda x: (order_map.get(x["stockout_risk_level"], 4), x["days_of_inventory"]))
        return results
