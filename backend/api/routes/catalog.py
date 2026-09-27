from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Optional

from backend.app.core.database import get_db
from backend.app.services.services import SupplyChainService

router = APIRouter()

@router.get("/api/products", tags=["Catalog"])
@router.get("/products", tags=["Catalog"])
def get_products(db: Session = Depends(get_db)):
    try:
        service = SupplyChainService(db)
        prods = service.product_repo.get_all()
        result = []
        for p in prods:
            cat_name = "General"
            if hasattr(p, "category") and p.category:
                cat_name = p.category.name if hasattr(p.category, "name") else str(p.category)
            result.append({
                "id": p.id,
                "sku": p.sku,
                "name": p.name,
                "category_id": getattr(p, "category_id", 1),
                "category_name": cat_name,
                "unit": getattr(p, "unit", "Units"),
                "unit_cost": getattr(p, "unit_cost", 0.0),
                "selling_price": getattr(p, "selling_price", 0.0),
                "lead_time_days": getattr(p, "lead_time_days", 7),
                "safety_stock_min": getattr(p, "safety_stock_min", 10),
                "reorder_point": getattr(p, "reorder_point", 20),
                "created_at": p.created_at.isoformat() if hasattr(p, "created_at") and p.created_at else None
            })
        return result
    except Exception as e:
        print(f"Get Products Exception Note: {e}")
        return []

@router.get("/api/warehouses", tags=["Catalog"])
@router.get("/warehouses", tags=["Catalog"])
def get_warehouses(db: Session = Depends(get_db)):
    try:
        service = SupplyChainService(db)
        whs = service.warehouse_repo.get_all()
        return [{
            "id": w.id,
            "code": getattr(w, "code", f"WH-{w.id}"),
            "name": w.name,
            "location": getattr(w, "location", "Main Hub"),
            "capacity": getattr(w, "capacity_sqft", 25000),
            "created_at": w.created_at.isoformat() if hasattr(w, "created_at") and w.created_at else None
        } for w in whs]
    except Exception as e:
        print(f"Get Warehouses Exception Note: {e}")
        return []

@router.get("/api/inventory", tags=["Inventory"])
@router.get("/inventory", tags=["Inventory"])
def get_inventory(warehouse_id: Optional[int] = None, db: Session = Depends(get_db)):
    try:
        service = SupplyChainService(db)
        items = service.inventory_repo.get_all(warehouse_id)
        result = []
        for i in items:
            prod_sku = ""
            prod_name = ""
            prod_unit_cost = 0.0
            if hasattr(i, "product") and i.product:
                prod_sku = getattr(i.product, "sku", "")
                prod_name = getattr(i.product, "name", "")
                prod_unit_cost = getattr(i.product, "unit_cost", 0.0)

            wh_name = ""
            if hasattr(i, "warehouse") and i.warehouse:
                wh_name = getattr(i.warehouse, "name", "")

            cur_stock = getattr(i, "current_stock", 0)
            alloc_stock = getattr(i, "allocated_stock", getattr(i, "reserved_stock", 0))
            avail_stock = getattr(i, "available_stock", max(0, cur_stock - alloc_stock))
            safe_stock = getattr(i, "safety_stock", 10)
            last_upd = getattr(i, "updated_at", getattr(i, "last_restock_date", None))

            result.append({
                "id": i.id,
                "product_id": getattr(i, "product_id", 0),
                "sku": prod_sku,
                "product_name": prod_name,
                "warehouse_id": getattr(i, "warehouse_id", 1),
                "warehouse_name": wh_name,
                "current_stock": cur_stock,
                "allocated_stock": alloc_stock,
                "available_stock": avail_stock,
                "safety_stock": safe_stock,
                "unit_cost": prod_unit_cost,
                "total_value": round(cur_stock * prod_unit_cost, 2),
                "last_updated": last_upd.isoformat() if last_upd and hasattr(last_upd, "isoformat") else None
            })
        return result
    except Exception as e:
        print(f"Get Inventory Exception Note: {e}")
        return []

@router.get("/api/suppliers", tags=["Suppliers"])
@router.get("/suppliers", tags=["Suppliers"])
def get_suppliers(db: Session = Depends(get_db)):
    try:
        service = SupplyChainService(db)
        sups = service.supplier_repo.get_all()
        return [{
            "id": s.id,
            "code": getattr(s, "code", f"SUP-{s.id}"),
            "name": s.name,
            "contact_email": getattr(s, "contact_email", None),
            "rating": getattr(s, "rating", 4.5),
            "lead_time_avg_days": getattr(s, "lead_time_avg_days", 7)
        } for s in sups]
    except Exception as e:
        print(f"Get Suppliers Exception Note: {e}")
        return []
