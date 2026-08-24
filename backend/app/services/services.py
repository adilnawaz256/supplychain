from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from backend.app.repositories.repositories import (
    ProductRepository, WarehouseRepository, InventoryRepository, SalesRepository, SupplierRepository
)
from backend.app.models.models import Order, PurchaseOrder, SalesHistory
from ai.forecasting.engine import StatisticalForecastEngine
from ai.inventory.optimization import InventoryOptimizer
from ai.risk.engine import InventoryRiskEngine

class SupplyChainService:
    def __init__(self, db: Session):
        self.db = db
        self.product_repo = ProductRepository(db)
        self.warehouse_repo = WarehouseRepository(db)
        self.inventory_repo = InventoryRepository(db)
        self.sales_repo = SalesRepository(db)
        self.supplier_repo = SupplierRepository(db)
        
        self.forecast_engine = StatisticalForecastEngine(db)
        self.optimizer = InventoryOptimizer(db)
        self.risk_engine = InventoryRiskEngine(db)

    def get_control_tower_summary((self)) -> Dict[str, Any]:
        products = self.product_repo.get_all()
        warehouses = self.warehouse_repo.get_all()
        inventory_items = self.inventory_repo.get_all()
        
        total_inv_value = sum(item.current_stock * item.product.unit_cost for item in inventory_items if item.product)
        
        risks = self.risk_engine.get_all_inventory_risks()
        critical_count = sum(1 for r in risks if r["stockout_risk_level"] == "CRITICAL")
        high_count = sum(1 for r in risks if r["stockout_risk_level"] == "HIGH")
        excess_count = sum(1 for r in risks if r["stockout_risk_level"] == "LOW")

        open_pos = self.db.query(PurchaseOrder).filter(PurchaseOrder.status.in_(["PENDING", "ISSUED"])).count()
        
        # 30 day sales revenue
        sales_30d = self.db.query(SalesHistory.revenue).all()
        rev_total = sum(s[0] for s in sales_30d) if sales_30d else 0.0

        top_risks = [r for r in risks if r["stockout_risk_level"] in ["CRITICAL", "HIGH"]][:10]

        return {
            "total_products": len(products),
            "total_warehouses": len(warehouses),
            "total_inventory_items": len(inventory_items),
            "total_inventory_value": round(total_inv_value, 2),
            "stockout_critical_count": critical_count,
            "stockout_high_count": high_count,
            "excess_inventory_count": excess_count,
            "open_purchase_orders": open_pos,
            "recent_sales_30d_revenue": round(rev_total, 2),
            "top_risk_products": top_risks
        }

    def get_inventory_recommendations(self) -> List[Dict[str, Any]]:
        risks = self.risk_engine.get_all_inventory_risks()
        recommendations = []
        for r in risks:
            if r["recommended_order_quantity"] > 0 or r["stockout_risk_level"] in ["CRITICAL", "HIGH"]:
                recommendations.append({
                    "sku": r["sku"],
                    "product_name": r["product_name"],
                    "warehouse": r["warehouse_name"],
                    "risk_level": r["stockout_risk_level"],
                    "current_stock": r["current_stock"],
                    "reorder_point": r["reorder_point"],
                    "days_of_inventory": r["days_of_inventory"],
                    "recommended_reorder_qty": r["recommended_order_quantity"],
                    "supplier": r["supplier_name"],
                    "lead_time_days": r["lead_time_days"],
                    "action_required": f"Issue PO for {r['recommended_order_quantity']} units with {r['supplier_name']}" if r["recommended_order_quantity"] > 0 else "Monitor closely"
                })
        return recommendations
