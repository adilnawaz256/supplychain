from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.app.models.models import Product, Inventory, SalesHistory, Supplier, SupplierProduct, RetailSpace, Order, OrderItem

class DataValidationEngine:
    """
    Data Quality & Readiness Validation Engine for Wisualyst Platform.
    Evaluates dataset health and calculates readiness scores (%) dynamically for all 4 intelligence modules.
    """
    def __init__(self, db: Session):
        self.db = db

    def evaluate_readiness(self) -> Dict[str, Any]:
        product_count = self.db.query(Product).count()
        inventory_count = self.db.query(Inventory).count()
        sales_count = self.db.query(SalesHistory).count()
        supplier_count = self.db.query(Supplier).count()
        space_count = self.db.query(RetailSpace).count()

        # Readiness = share of products that have the data each module needs (real coverage, 0-100%).
        def coverage(column) -> float:
            if product_count == 0:
                return 0.0
            covered = self.db.query(func.count(func.distinct(column))).scalar() or 0
            return round(min(100.0, covered * 100.0 / product_count), 1)

        inv_readiness = coverage(Inventory.product_id)
        demand_readiness = coverage(SalesHistory.product_id)
        proc_readiness = coverage(SupplierProduct.product_id)
        assort_readiness = coverage(RetailSpace.product_id)
        order_line_count = self.db.query(OrderItem).count()
        customer_orders = self.db.query(Order).filter(Order.customer_id.isnot(None)).count()

        overall_score = round((inv_readiness + demand_readiness + proc_readiness + assort_readiness) / 4.0, 1)

        quality_checks = []
        if product_count > 0:
            quality_checks.append({"check": "Product Catalog Schema Mapped", "status": "PASSED", "severity": "NONE", "affected_records": 0})
        else:
            quality_checks.append({"check": "Product Catalog Schema Mapped", "status": "PENDING", "severity": "HIGH", "affected_records": 0})

        if sales_count > 0:
            quality_checks.append({"check": "Historical Sales Coverage", "status": "PASSED", "severity": "NONE", "affected_records": 0})
        else:
            quality_checks.append({"check": "Historical Sales Coverage", "status": "PENDING", "severity": "MEDIUM", "affected_records": 0})

        return {
            "overall_readiness_pct": overall_score,
            "can_launch_workspace": overall_score >= 50.0,
            "modules": {
                "inventory_ai": {"readiness_pct": inv_readiness, "status": "READY" if inv_readiness >= 50 else "PENDING_DATA"},
                "demand_ai": {"readiness_pct": demand_readiness, "status": "READY" if demand_readiness >= 50 else "PENDING_DATA"},
                "procurement_ai": {"readiness_pct": proc_readiness, "status": "READY" if proc_readiness >= 50 else "PENDING_DATA"},
                "assortment_ai": {"readiness_pct": assort_readiness, "status": "READY" if assort_readiness >= 50 else "PENDING_DATA"},
                "pricing_ai": {"readiness_pct": demand_readiness, "status": "READY" if demand_readiness >= 50 else "PENDING_DATA"},
                "policy_simulation_ai": {"readiness_pct": min(inv_readiness, demand_readiness), "status": "READY" if min(inv_readiness, demand_readiness) >= 50 else "PENDING_DATA"},
                "customer_ltv_ai": {"readiness_pct": 100.0 if customer_orders > 0 else 0.0, "status": "READY" if customer_orders > 0 else "PENDING_DATA"},
                "market_basket_ai": {"readiness_pct": 100.0 if order_line_count > 0 else 0.0, "status": "READY" if order_line_count > 0 else "PENDING_DATA"},
                "trade_area_ai": {"readiness_pct": 0.0, "status": "PENDING_DATA"}
            },
            "dataset_summary": {
                "products_mapped": product_count,
                "inventory_items_mapped": inventory_count,
                "sales_history_records": sales_count,
                "suppliers_connected": supplier_count,
                "retail_store_spaces": space_count
            },
            "quality_checks": quality_checks
        }
