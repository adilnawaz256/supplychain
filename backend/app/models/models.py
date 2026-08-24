from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Enum, Index
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from backend.app.core.database import Base

class RiskLevel(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class OrderStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"

class ProductCategory(Base):
    __tablename__ = "product_categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    products = relationship("Product", back_populates="category")

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String(50), nullable=False, unique=True, index=True)
    name = Column(String(200), nullable=False)
    category_id = Column(Integer, ForeignKey("product_categories.id"), nullable=False)
    unit = Column(String(20), default="Units")
    unit_cost = Column(Float, nullable=False, default=0.0)
    selling_price = Column(Float, nullable=False, default=0.0)
    lead_time_days = Column(Integer, nullable=False, default=7)
    safety_stock_min = Column(Integer, nullable=False, default=10)
    reorder_point = Column(Integer, nullable=False, default=20)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    category = relationship("ProductCategory", back_populates="products")
    inventory = relationship("Inventory", back_populates="product")
    sales_history = relationship("SalesHistory", back_populates="product")
    supplier_products = relationship("SupplierProduct", back_populates="product")
    order_items = relationship("OrderItem", back_populates="product")
    purchase_order_items = relationship("PurchaseOrderItem", back_populates="product")

class Warehouse(Base):
    __tablename__ = "warehouses"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), nullable=False, unique=True, index=True)
    name = Column(String(150), nullable=False)
    location = Column(String(200), nullable=False)
    capacity = Column(Integer, nullable=False, default=10000)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    inventory = relationship("Inventory", back_populates="warehouse")
    sales_history = relationship("SalesHistory", back_populates="warehouse")
    orders = relationship("Order", back_populates="warehouse")
    purchase_orders = relationship("PurchaseOrder", back_populates="warehouse")
    shipments = relationship("Shipment", back_populates="warehouse")

class Inventory(Base):
    __tablename__ = "inventory"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False, index=True)
    current_stock = Column(Integer, nullable=False, default=0)
    allocated_stock = Column(Integer, nullable=False, default=0)
    available_stock = Column(Integer, nullable=False, default=0)
    safety_stock = Column(Integer, nullable=False, default=10)
    max_stock_capacity = Column(Integer, nullable=False, default=1000)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    product = relationship("Product", back_populates="inventory")
    warehouse = relationship("Warehouse", back_populates="inventory")

class InventoryTransaction(Base):
    __tablename__ = "inventory_transactions"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False)
    transaction_type = Column(String(50), nullable=False) # INBOUND, OUTBOUND, ADJUSTMENT
    quantity = Column(Integer, nullable=False)
    reference_id = Column(String(100), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

class SalesHistory(Base):
    __tablename__ = "sales_history"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False, index=True)
    date = Column(DateTime, nullable=False, index=True)
    quantity_sold = Column(Integer, nullable=False)
    revenue = Column(Float, nullable=False, default=0.0)

    product = relationship("Product", back_populates="sales_history")
    warehouse = relationship("Warehouse", back_populates="sales_history")

class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    email = Column(String(150), nullable=True)
    region = Column(String(100), nullable=False, default="Default")
    created_at = Column(DateTime, default=datetime.utcnow)

    orders = relationship("Order", back_populates="customer")

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    order_number = Column(String(100), nullable=False, unique=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False)
    order_date = Column(DateTime, default=datetime.utcnow)
    status = Column(String(50), default="PENDING")
    total_amount = Column(Float, default=0.0)

    customer = relationship("Customer", back_populates="orders")
    warehouse = relationship("Warehouse", back_populates="orders")
    items = relationship("OrderItem", back_populates="order")
    shipment = relationship("Shipment", back_populates="order", uselist=False)

class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)

    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")

class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), nullable=False, unique=True, index=True)
    name = Column(String(150), nullable=False)
    contact_email = Column(String(150), nullable=True)
    rating = Column(Float, default=4.5)
    lead_time_avg_days = Column(Integer, default=7)
    created_at = Column(DateTime, default=datetime.utcnow)

    supplier_products = relationship("SupplierProduct", back_populates="supplier")
    purchase_orders = relationship("PurchaseOrder", back_populates="supplier")

class SupplierProduct(Base):
    __tablename__ = "supplier_products"

    id = Column(Integer, primary_key=True, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    supplier_sku = Column(String(100), nullable=True)
    contracted_price = Column(Float, nullable=False)
    lead_time_days = Column(Integer, nullable=False, default=7)

    supplier = relationship("Supplier", back_populates="supplier_products")
    product = relationship("Product", back_populates="supplier_products")

class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id = Column(Integer, primary_key=True, index=True)
    po_number = Column(String(100), nullable=False, unique=True, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False)
    status = Column(String(50), default="PENDING") # PENDING, ISSUED, RECEIVED, CANCELLED
    expected_delivery_date = Column(DateTime, nullable=True)
    total_cost = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    supplier = relationship("Supplier", back_populates="purchase_orders")
    warehouse = relationship("Warehouse", back_populates="purchase_orders")
    items = relationship("PurchaseOrderItem", back_populates="purchase_order")

class PurchaseOrderItem(Base):
    __tablename__ = "purchase_order_items"

    id = Column(Integer, primary_key=True, index=True)
    purchase_order_id = Column(Integer, ForeignKey("purchase_orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_cost = Column(Float, nullable=False)

    purchase_order = relationship("PurchaseOrder", back_populates="items")
    product = relationship("Product", back_populates="purchase_order_items")

class Shipment(Base):
    __tablename__ = "shipments"

    id = Column(Integer, primary_key=True, index=True)
    tracking_number = Column(String(100), nullable=False, unique=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False)
    carrier = Column(String(100), default="Standard Express")
    status = Column(String(50), default="IN_TRANSIT")
    shipped_date = Column(DateTime, default=datetime.utcnow)
    estimated_delivery = Column(DateTime, nullable=True)

    order = relationship("Order", back_populates="shipment")
    warehouse = relationship("Warehouse", back_populates="shipments")
