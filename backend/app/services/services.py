
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict, Any, Optional
from backend.app.repositories.repositories import (
    ProductRepository, WarehouseRepository, InventoryRepository, SalesRepository, SupplierRepository
)
from backend.app.models.models import Product, Warehouse, Inventory, Order, PurchaseOrder, SalesHistory, Supplier
from backend.ml.forecasting.engine import StatisticalForecastEngine
from backend.ml.inventory.optimization import InventoryOptimizer
from backend.ml.risk.engine import InventoryRiskEngine
from backend.ml.procurement.engine import ProcurementOptimizerEngine
from backend.ml.assortment.engine import AssortmentOptimizerEngine
from backend.ml.pricing.engine import PricingOptimizationEngine
from backend.ml.policy.engine import InventoryPolicySimulationEngine
from backend.ml.customer.engine import CustomerLTVSegmentationEngine
from backend.ml.cross_sell.engine import MarketBasketRecommendationEngine
from backend.ml.trade_area.engine import TradeAreaModellingEngine
from backend.app.services.recommendation_engine import UnifiedRecommendationEngine
from backend.app.services.mapping_engine import CanonicalMappingEngine
from backend.app.services.validation_engine import DataValidationEngine

import time
from datetime import datetime, timedelta

SUMMARY_CACHE: Dict[str, Any] = {"timestamp": 0, "data": None}

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
        self.procurement_engine = ProcurementOptimizerEngine(db)
        self.assortment_engine = AssortmentOptimizerEngine(db)
        self.pricing_engine = PricingOptimizationEngine(db)
        self.policy_simulation_engine = InventoryPolicySimulationEngine(db)
        self.customer_ltv_engine = CustomerLTVSegmentationEngine(db)
        self.market_basket_engine = MarketBasketRecommendationEngine(db)
        self.trade_area_engine = TradeAreaModellingEngine(db)
        self.recommendation_engine = UnifiedRecommendationEngine(db)
        self.mapping_engine = CanonicalMappingEngine()
        self.validation_engine = DataValidationEngine(db)

    def get_control_tower_summary(self) -> Dict[str, Any]:
        global SUMMARY_CACHE
        now = time.time()
        if (now - SUMMARY_CACHE["timestamp"]) < 30 and SUMMARY_CACHE["data"]:
            return SUMMARY_CACHE["data"]

        total_prods = self.db.query(Product).count()
        total_whs = self.db.query(Warehouse).count()
        total_inv_items = self.db.query(Inventory).count()

        readiness = self.validation_engine.evaluate_readiness()

        if total_prods == 0:
            res = {
                "total_products": 0,
                "total_warehouses": total_whs,
                "total_inventory_items": total_inv_items,
                "total_inventory_value": 0.0,
                "stockout_critical_count": 0,
                "stockout_high_count": 0,
                "excess_inventory_count": 0,
                "open_purchase_orders": self.db.query(PurchaseOrder).filter(PurchaseOrder.status.in_(["PENDING", "ISSUED", "OPEN"])).count(),
                "recent_sales_30d_revenue": None,
                "recent_sales_window_end": None,
                "top_risk_products": [],
                "potential_savings": None,
                "avg_supplier_otif": None,
                "avg_store_gmroi": None,
                "overall_readiness_pct": readiness.get("overall_readiness_pct"),
                "modules_readiness": readiness.get("modules"),
                "dataset_summary": readiness.get("dataset_summary"),
                "can_launch_workspace": readiness.get("can_launch_workspace")
            }
            SUMMARY_CACHE["timestamp"] = now
            SUMMARY_CACHE["data"] = res
            return res

        # Fast SQL sum for total inventory value
        total_inv_value = float(
            self.db.query(func.coalesce(func.sum(Inventory.current_stock * Product.unit_cost), 0.0))
            .join(Product, Inventory.product_id == Product.id)
            .scalar() or 0.0
        )

        risks = self.risk_engine.get_all_inventory_risks()
        critical_count = sum(1 for r in risks if r["stockout_risk_level"] == "CRITICAL")
        high_count = sum(1 for r in risks if r["stockout_risk_level"] == "HIGH")
        excess_count = sum(1 for r in risks if r["stockout_risk_level"] == "LOW")

        open_pos = self.db.query(PurchaseOrder).filter(PurchaseOrder.status.in_(["PENDING", "ISSUED", "OPEN"])).count()

        # Revenue over the last 30 days up to the latest sale date in sales_history
        latest_sale = self.db.query(func.max(SalesHistory.date)).scalar()
        if latest_sale is not None and not isinstance(latest_sale, datetime):
            latest_sale = datetime.fromisoformat(str(latest_sale))
        if latest_sale is not None:
            recent_rev: Optional[float] = round(float(
                self.db.query(func.coalesce(func.sum(SalesHistory.revenue), 0.0))
                .filter(SalesHistory.date > latest_sale - timedelta(days=30), SalesHistory.date <= latest_sale)
                .scalar() or 0.0
            ), 2)
        else:
            recent_rev = None

        top_risks = [r for r in risks if r["stockout_risk_level"] in ["CRITICAL", "HIGH"]][:10]

        # Supplier OTIF: average of the suppliers that have an otif_score
        otif_avg = self.db.query(func.avg(Supplier.otif_score)).filter(Supplier.otif_score.isnot(None)).scalar()
        avg_otif = round(float(otif_avg), 1) if otif_avg is not None else None

        # GMROI: (all-time sales revenue - cost of goods sold) / current inventory value at cost
        rev_total = float(self.db.query(func.coalesce(func.sum(SalesHistory.revenue), 0.0)).scalar() or 0.0)
        total_cogs = float(
            self.db.query(func.coalesce(func.sum(SalesHistory.quantity_sold * Product.unit_cost), 0.0))
            .join(Product, SalesHistory.product_id == Product.id)
            .scalar() or 0.0
        )
        has_sales = latest_sale is not None
        dyn_gmroi = round((rev_total - total_cogs) / total_inv_value, 2) if (has_sales and total_inv_value > 0) else None

        # Potential procurement savings: only the procurement engine's computed value
        proc_intel = self.procurement_engine.generate_procurement_intelligence()
        potential_savings = proc_intel.get("potential_savings")

        res = {
            "total_products": total_prods,
            "total_warehouses": total_whs,
            "total_inventory_items": total_inv_items,
            "total_inventory_value": round(total_inv_value, 2),
            "stockout_critical_count": critical_count,
            "stockout_high_count": high_count,
            "excess_inventory_count": excess_count,
            "open_purchase_orders": open_pos,
            "recent_sales_30d_revenue": recent_rev,
            "recent_sales_window_end": latest_sale.isoformat() if latest_sale is not None else None,
            "top_risk_products": top_risks,
            "potential_savings": round(potential_savings, 2) if potential_savings is not None else None,
            "avg_supplier_otif": avg_otif,
            "avg_store_gmroi": dyn_gmroi,
            "overall_readiness_pct": readiness.get("overall_readiness_pct"),
            "modules_readiness": readiness.get("modules"),
            "dataset_summary": readiness.get("dataset_summary"),
            "can_launch_workspace": readiness.get("can_launch_workspace")
        }
        SUMMARY_CACHE["timestamp"] = now
        SUMMARY_CACHE["data"] = res
        return res

    def get_inventory_recommendations(self) -> List[Dict[str, Any]]:
        return self.recommendation_engine.get_unified_recommendations()

    def get_pricing_optimization(self) -> Dict[str, Any]:
        return self.pricing_engine.get_pricing_intelligence()

    def get_policy_simulation(self) -> Dict[str, Any]:
        return self.policy_simulation_engine.get_policy_simulation_intelligence()

    def get_customer_ltv(self) -> Dict[str, Any]:
        return self.customer_ltv_engine.get_customer_ltv_intelligence()

    def get_market_basket(self) -> Dict[str, Any]:
        return self.market_basket_engine.get_market_basket_intelligence()

    def get_trade_area(self) -> Dict[str, Any]:
        return self.trade_area_engine.get_trade_area_intelligence()
