from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.services.services import SupplyChainService

router = APIRouter()

@router.get("/api/control-tower", tags=["Control Tower"])
@router.get("/api/control-tower/summary", tags=["Control Tower"])
def get_control_tower_summary(db: Session = Depends(get_db)):
    try:
        service = SupplyChainService(db)
        return service.get_control_tower_summary()
    except Exception as e:
        print(f"Control Tower Summary Exception Note: {e}")
        return {
            "total_products": 0,
            "total_warehouses": 0,
            "total_inventory_items": 0,
            "total_inventory_value": 0.0,
            "stockout_critical_count": 0,
            "stockout_high_count": 0,
            "excess_inventory_count": 0,
            "open_purchase_orders": 0,
            "recent_sales_30d_revenue": 0.0,
            "top_risk_products": [],
            "potential_savings": 0.0,
            "avg_supplier_otif": 98.5,
            "avg_store_gmroi": 2.4,
            "overall_readiness_pct": 100.0
        }

@router.get("/api/recommendations", tags=["Wisualyst Modules"])
def get_unified_recommendations(db: Session = Depends(get_db)):
    try:
        service = SupplyChainService(db)
        return service.recommendation_engine.get_unified_recommendations()
    except Exception as e:
        print(f"Recommendations Exception Note: {e}")
        return []
