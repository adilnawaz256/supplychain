from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Optional

from backend.app.core.database import get_db
from backend.app.services.services import SupplyChainService

router = APIRouter()

@router.get("/api/products", tags=["Catalog"])
@router.get("/products", tags=["Catalog"])
def get_products(db: Session = Depends(get_db)):
    service = SupplyChainService(db)
    prods = service.product_repo.get_all()
    return [{
        "id": p.id,
        "sku": p.sku,
        "name": p.name,
        "category_id": p.category_id,
        "category_name": p.category.name if p.category else "Uncategorized",
        "unit": p.unit,
        "unit_cost": p.unit_cost,
        "selling_price": p.selling_price,
        "lead_time_days": p.lead_time_days,
        "safety_stock_min": p.safety_stock_min,
        "reorder_point": p.reorder_point,
        "created_at": p.created_at.isoformat() if p.created_at else None
    } for p in prods]

@router.get("/api/warehouses", tags=["Catalog"])
@router.get("/warehouses", tags=["Catalog"])
def get_warehouses(db: Session = Depends(get_db)):
    service = SupplyChainService(db)
    whs = service.warehouse_repo.get_all()
    return [{
        "id": w.id, "code": w.code, "name": w.name, "location": w.location, "capacity": getattr(w, "capacity_sqft", 25000),
        "created_at": w.created_at.isoformat() if w.created_at else None
    } for w in whs]

@router.get("/api/inventory", tags=["Inventory"])
@router.get("/inventory", tags=["Inventory"])
def get_inventory(warehouse_id: Optional[int] = None, db: Session = Depends(get_db)):
    service = SupplyChainService(db)
    items = service.inventory_repo.get_all(warehouse_id)
    return [{
        "id": i.id,
        "product_id": i.product_id,
        "sku": i.product.sku if i.product else "",
        "product_name": i.product.name if i.product else "",
        "warehouse_id": i.warehouse_id,
        "warehouse_name": i.warehouse.name if i.warehouse else "",
        "current_stock": i.current_stock,
        "allocated_stock": i.allocated_stock,
        "available_stock": i.available_stock,
        "safety_stock": i.safety_stock,
        "unit_cost": i.product.unit_cost if i.product else 0.0,
        "total_value": round(i.current_stock * (i.product.unit_cost if i.product else 0.0), 2),
        "last_updated": i.last_updated.isoformat() if i.last_updated else None
    } for i in items]

@router.get("/api/suppliers", tags=["Suppliers"])
@router.get("/suppliers", tags=["Suppliers"])
def get_suppliers(db: Session = Depends(get_db)):
    service = SupplyChainService(db)
    sups = service.supplier_repo.get_all()
    return [{
        "id": s.id, "code": s.code, "name": s.name, "contact_email": s.contact_email,
        "rating": s.rating, "lead_time_avg_days": s.lead_time_avg_days
    } for s in sups]
