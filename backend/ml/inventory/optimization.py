import math
import numpy as np
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from backend.app.models.models import Inventory, Product, Warehouse, SalesHistory

# Business settings (no table holds these); echoed under "settings" in the output
SERVICE_LEVEL_Z = 1.65      # z-score for a 95% target service level
SALES_LOOKBACK_ROWS = 60    # most recent sales rows used for mean / std
TARGET_SS_MULTIPLE = 2      # order-up-to target = ROP + this * safety stock
EXCESS_ROP_MULTIPLE = 4     # stock above this * ROP counts as excess


class InventoryOptimizer:
    """
    Implements deterministic supply chain optimization formulas:
    - Daily Demand (D_avg) & Standard Deviation (sigma_d)
    - Safety Stock SS = Z * sigma_d * sqrt(L)
    - Reorder Point ROP = (D_avg * L) + SS
    - Recommended Order Quantity ROQ = max(0, ROP + TARGET_SS_MULTIPLE * SS - Current_Stock) when Current_Stock <= ROP
    Values that need sales history are None when the product/warehouse has no sales rows.
    """
    def __init__(self, db: Session, service_level_z: float = SERVICE_LEVEL_Z):
        self.db = db
        self.z = service_level_z

    def calculate_inventory_metrics(self, product_id: int, warehouse_id: int) -> Dict[str, Any]:
        product = self.db.query(Product).filter(Product.id == product_id).first()
        warehouse = self.db.query(Warehouse).filter(Warehouse.id == warehouse_id).first()
        inv = self.db.query(Inventory).filter(
            Inventory.product_id == product_id,
            Inventory.warehouse_id == warehouse_id
        ).first()

        if not product or not warehouse or not inv:
            raise ValueError("Invalid product, warehouse, or inventory record")

        # Last SALES_LOOKBACK_ROWS sales rows for this product/warehouse to estimate demand variability
        sales = self.db.query(SalesHistory.quantity_sold).filter(
            SalesHistory.product_id == product_id,
            SalesHistory.warehouse_id == warehouse_id
        ).order_by(SalesHistory.date.desc()).limit(SALES_LOOKBACK_ROWS).all()

        qty_list = [s[0] for s in sales if s[0] is not None]
        d_avg: Optional[float] = float(np.mean(qty_list)) if qty_list else None
        # Standard deviation needs at least 2 observations; otherwise unknown
        d_std: Optional[float] = float(np.std(qty_list)) if len(qty_list) > 1 else None

        lead_time = product.lead_time_days
        current_stock = inv.current_stock or 0
        reserved = inv.reserved_stock or 0

        # 1. Safety Stock (formula when std and lead time are known; never below the product's configured minimum)
        safety_stock_calc = None
        if d_std is not None and lead_time is not None:
            safety_stock_calc = int(math.ceil(self.z * d_std * math.sqrt(lead_time)))
        candidates = [v for v in (product.safety_stock_min, safety_stock_calc) if v is not None]
        safety_stock = max(candidates) if candidates else None

        # 2. Reorder Point (Expected demand during lead time + Safety stock)
        reorder_point = None
        if d_avg is not None and lead_time is not None and safety_stock is not None:
            reorder_point = int(math.ceil(d_avg * lead_time + safety_stock))

        # 3. Days of Inventory (DOI)
        doi = round(current_stock / d_avg, 1) if d_avg else None

        # 4. Recommended Order Quantity: order up to ROP + TARGET_SS_MULTIPLE * SS when at/below ROP
        if reorder_point is None:
            roq = None
        elif current_stock <= reorder_point:
            roq = max(0, reorder_point + safety_stock * TARGET_SS_MULTIPLE - current_stock)
        else:
            roq = 0

        # 5. Stockout & Excess Assessment
        is_stockout_risk = (current_stock <= reorder_point) if reorder_point is not None else None
        is_excess_stock = (current_stock > reorder_point * EXCESS_ROP_MULTIPLE) if reorder_point is not None else None

        return {
            "product_id": product.id,
            "sku": product.sku,
            "product_name": product.name,
            "warehouse_id": warehouse.id,
            "warehouse_name": warehouse.name,
            "current_stock": current_stock,
            "allocated_stock": reserved,
            "available_stock": max(0, current_stock - reserved),
            "avg_daily_demand": round(d_avg, 2) if d_avg is not None else None,
            "demand_std_dev": round(d_std, 2) if d_std is not None else None,
            "sales_rows_used": len(qty_list),
            "lead_time_days": lead_time,
            "safety_stock_calculated": safety_stock,
            "reorder_point_calculated": reorder_point,
            "days_of_inventory": doi,
            "is_stockout_risk": is_stockout_risk,
            "is_excess_stock": is_excess_stock,
            "recommended_order_quantity": int(roq) if roq is not None else None,
            "settings": {
                "service_level_z": self.z,
                "sales_lookback_rows": SALES_LOOKBACK_ROWS,
                "target_ss_multiple": TARGET_SS_MULTIPLE,
                "excess_rop_multiple": EXCESS_ROP_MULTIPLE,
            }
        }
