from sqlalchemy.orm import Session
from typing import List, Optional
from backend.app.models.models import (
    Product, Warehouse, Inventory, SalesHistory, Supplier, Order, PurchaseOrder, ProductCategory
)

class ProductRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all(self, skip: int = 0, limit: int = 100) -> List[Product]:
        try:
            return self.db.query(Product).offset(skip).limit(limit).all()
        except Exception as e:
            print(f"ProductRepository get_all note: {e}")
            return []

    def get_by_id(self, product_id: int) -> Optional[Product]:
        try:
            return self.db.query(Product).filter(Product.id == product_id).first()
        except Exception:
            return None

    def get_by_sku(self, sku: str) -> Optional[Product]:
        try:
            return self.db.query(Product).filter(Product.sku == sku.upper()).first()
        except Exception:
            return None

class WarehouseRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all(self) -> List[Warehouse]:
        try:
            return self.db.query(Warehouse).all()
        except Exception:
            return []

    def get_by_id(self, warehouse_id: int) -> Optional[Warehouse]:
        try:
            return self.db.query(Warehouse).filter(Warehouse.id == warehouse_id).first()
        except Exception:
            return None

class InventoryRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all(self, warehouse_id: Optional[int] = None) -> List[Inventory]:
        try:
            query = self.db.query(Inventory)
            if warehouse_id:
                query = query.filter(Inventory.warehouse_id == warehouse_id)
            return query.all()
        except Exception as e:
            print(f"InventoryRepository get_all note: {e}")
            return []

    def get_by_product_and_warehouse(self, product_id: int, warehouse_id: int) -> Optional[Inventory]:
        try:
            return self.db.query(Inventory).filter(
                Inventory.product_id == product_id,
                Inventory.warehouse_id == warehouse_id
            ).first()
        except Exception:
            return None

class SalesRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_product(self, product_id: int, warehouse_id: Optional[int] = None, days: int = 90) -> List[SalesHistory]:
        try:
            query = self.db.query(SalesHistory).filter(SalesHistory.product_id == product_id)
            if warehouse_id:
                query = query.filter(SalesHistory.warehouse_id == warehouse_id)
            return query.order_by(SalesHistory.date.desc()).limit(days).all()
        except Exception:
            return []

class SupplierRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all(self) -> List[Supplier]:
        try:
            return self.db.query(Supplier).all()
        except Exception:
            return []

    def get_by_id(self, supplier_id: int) -> Optional[Supplier]:
        try:
            return self.db.query(Supplier).filter(Supplier.id == supplier_id).first()
        except Exception:
            return None
