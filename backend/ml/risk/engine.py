import time
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session, joinedload
from backend.app.models.models import Inventory, Product, Warehouse, Supplier, SupplierProduct, SalesHistory
from sqlalchemy import func

# Simple in-memory cache for 30 seconds
RISK_CACHE: Dict[str, Any] = {"timestamp": 0, "data": []}

# Business settings (no table holds these); echoed in each item's calculation_trace.settings
ORDER_UP_TO_ROP_MULTIPLE = 2   # when at/below ROP, order up to this multiple of the reorder point
LEAD_TIME_BUFFER_DAYS = 3      # DOI within lead time + this many days -> HIGH
EXCESS_DOI_DAYS = 60.0         # DOI above this -> LOW (excess)
EXCESS_ROP_MULTIPLE = 4        # stock above this multiple of ROP -> LOW (excess)

class InventoryRiskEngine:
    def __init__(self, db: Session):
        self.db = db

    def get_all_inventory_risks(self, warehouse_id: Optional[int] = None, risk_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        global RISK_CACHE
        now = time.time()
        
        # Return cached risks if valid within 30 seconds and no filters applied
        if not warehouse_id and not risk_filter and (now - RISK_CACHE["timestamp"]) < 30 and RISK_CACHE["data"]:
            return RISK_CACHE["data"]

        # 1. Fast flat column query to eliminate ORM loading overhead for 9,243 rows
        query = self.db.query(
            Inventory.product_id,
            Inventory.warehouse_id,
            Inventory.current_stock,
            Inventory.reserved_stock,
            Product.sku,
            Product.name.label("product_name"),
            Product.lead_time_days,
            Product.safety_stock_min,
            Product.reorder_point,
            Warehouse.name.label("warehouse_name")
        ).join(Product, Inventory.product_id == Product.id)\
         .join(Warehouse, Inventory.warehouse_id == Warehouse.id)

        if warehouse_id:
            query = query.filter(Inventory.warehouse_id == warehouse_id)

        inventory_items = query.all()
        
        # 2. Average daily demand per product = units sold / calendar days covered by its sales
        sales_data = self.db.query(
            SalesHistory.product_id,
            func.sum(SalesHistory.quantity_sold),
            func.min(SalesHistory.date),
            func.max(SalesHistory.date)
        ).group_by(SalesHistory.product_id).all()

        avg_demand_map = {}
        for pid, total_qty, first_day, last_day in sales_data:
            days = 1
            if first_day and last_day:
                first_day = first_day if hasattr(first_day, "date") else datetime.fromisoformat(str(first_day))
                last_day = last_day if hasattr(last_day, "date") else datetime.fromisoformat(str(last_day))
                days = max(1, (last_day.date() - first_day.date()).days + 1)
            avg_demand_map[pid] = float(total_qty or 0) / days

        # 3. Supplier per product: the cheapest supplier_products link (same rule as procurement)
        sup_data = self.db.query(SupplierProduct.product_id, SupplierProduct.unit_cost, Supplier.name)\
            .join(Supplier, SupplierProduct.supplier_id == Supplier.id).all()
        supplier_map: Dict[int, Any] = {}
        for pid, link_cost, sup_name in sup_data:
            cur = supplier_map.get(pid)
            if cur is None or (link_cost is not None and (cur[0] is None or link_cost < cur[0])):
                supplier_map[pid] = (link_cost, sup_name)

        results = []
        for (product_id, wh_id, current_stock, reserved_stock, sku, product_name,
             lead_time_days, safety_stock_min, reorder_point, wh_name) in inventory_items:
            current_stock = current_stock or 0
            allocated_stock = reserved_stock or 0
            available_stock = max(0, current_stock - allocated_stock)

            has_sales = product_id in avg_demand_map
            avg_daily_demand = avg_demand_map.get(product_id) if has_sales else None
            forecast_7d = round(avg_daily_demand * 7, 1) if avg_daily_demand is not None else None
            lead_time = lead_time_days
            safety_stock = safety_stock_min
            rop = reorder_point
            doi = round(current_stock / avg_daily_demand, 1) if avg_daily_demand else None
            if rop is not None and current_stock <= rop:
                rec_order_qty = max(0, rop * ORDER_UP_TO_ROP_MULTIPLE - current_stock)
            else:
                rec_order_qty = 0
            supplier_name = supplier_map[product_id][1] if product_id in supplier_map else None

            doi_vs_lead = doi is not None and lead_time is not None
            notes = []
            if lead_time is None:
                notes.append("products.lead_time_days is empty: lead-time comparison skipped")
            if not has_sales:
                notes.append("no sales_history rows: demand, DOI and forecast unknown; level from stock thresholds only")
            elif doi is None:
                notes.append("zero units sold: DOI not computable")

            # Classification Logic
            if safety_stock is not None and current_stock < safety_stock:
                risk_level = "CRITICAL"
                reason = f"CRITICAL STOCKOUT RISK! Stock ({current_stock}) below safety stock ({safety_stock})."
            elif doi_vs_lead and doi < lead_time:
                risk_level = "CRITICAL"
                reason = f"CRITICAL STOCKOUT RISK! DOI ({doi}d) < Lead Time ({lead_time}d)."
            elif rop is not None and current_stock <= rop:
                risk_level = "HIGH"
                reason = f"High stockout risk. Stock ({current_stock}) at/below reorder point ({rop})." + (f" DOI is {doi} days." if doi is not None else "")
            elif doi_vs_lead and doi <= (lead_time + LEAD_TIME_BUFFER_DAYS):
                risk_level = "HIGH"
                reason = f"High stockout risk. DOI ({doi}d) within {LEAD_TIME_BUFFER_DAYS} days of lead time ({lead_time}d)."
            elif not has_sales or doi is None:
                risk_level = "MEDIUM"
                reason = f"Stock ({current_stock}) above reorder point ({rop}); demand unknown (no sales data)."
            elif doi > EXCESS_DOI_DAYS or (rop is not None and current_stock > rop * EXCESS_ROP_MULTIPLE):
                risk_level = "LOW"
                reason = f"Excess stock level ({current_stock} units, {doi} days supply)."
            else:
                risk_level = "MEDIUM"
                reason = f"Stable inventory level ({current_stock} units, {doi} days of supply)."

            item_res = {
                "product_id": product_id,
                "sku": sku,
                "product_name": product_name,
                "warehouse_id": wh_id,
                "warehouse_name": wh_name,
                "current_stock": current_stock,
                "allocated_stock": allocated_stock,
                "available_stock": available_stock,
                "avg_daily_demand": round(avg_daily_demand, 2) if avg_daily_demand is not None else None,
                "demand_known": has_sales,
                "forecast_7d_demand": forecast_7d,
                "lead_time_days": lead_time,
                "safety_stock": safety_stock,
                "reorder_point": rop,
                "days_of_inventory": doi,
                "stockout_risk_level": risk_level,
                "reasoning": reason,
                "recommended_order_quantity": rec_order_qty,
                "supplier_name": supplier_name,
                "calculation_trace": {
                    "demand_source": "sales_history (units sold / days covered)" if has_sales else "none: no sales_history rows",
                    "days_of_inventory_formula": "DOI = Current Stock / Average Daily Demand",
                    "recommended_order_formula": f"if stock <= ROP: {ORDER_UP_TO_ROP_MULTIPLE} * ROP - Current Stock, else 0",
                    "settings": {
                        "order_up_to_rop_multiple": ORDER_UP_TO_ROP_MULTIPLE,
                        "lead_time_buffer_days": LEAD_TIME_BUFFER_DAYS,
                        "excess_doi_days": EXCESS_DOI_DAYS,
                        "excess_rop_multiple": EXCESS_ROP_MULTIPLE,
                    },
                    "current_stock": current_stock,
                    "avg_daily_demand": round(avg_daily_demand, 2) if avg_daily_demand is not None else None,
                    "calculated_doi": f"{doi} days" if doi is not None else None,
                    "safety_threshold": f"{safety_stock} units" if safety_stock is not None else None,
                    "lead_time": f"{lead_time} days" if lead_time is not None else None,
                    "notes": notes,
                    "data_source_tables": "inventory (current_stock, reserved_stock), products (lead_time_days, safety_stock_min, reorder_point), sales_history, supplier_products, suppliers"
                }
            }

            if risk_filter:
                if risk_level == risk_filter.upper():
                    results.append(item_res)
            else:
                results.append(item_res)

        # Sort by risk severity (CRITICAL > HIGH > MEDIUM > LOW)
        severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        results.sort(key=lambda x: severity_order.get(x["stockout_risk_level"], 99))

        if not warehouse_id and not risk_filter:
            RISK_CACHE["timestamp"] = now
            RISK_CACHE["data"] = results

        return results
