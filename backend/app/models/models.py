from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from backend.app.core.database import Base

# --- 1. Auth & Team Governance Models ---
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(150), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=True)
    company_name = Column(String(150), nullable=True)
    role = Column(String(50), default="Admin")
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class WorkspaceMember(Base):
    __tablename__ = "workspace_members"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(150), nullable=False, unique=True)
    role = Column(String(50), default="Viewer")
    status = Column(String(20), default="Active")
    initials = Column(String(10), default="U")
    color = Column(String(20), default="#2563eb")
    bg = Column(String(20), default="#eff6ff")
    created_at = Column(DateTime, default=datetime.utcnow)

class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    role_key = Column(String(50), nullable=False, unique=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    scope = Column(String(100), default="Full Access")
    scope_color = Column(String(20), default="#7c3aed")
    scope_bg = Column(String(20), default="#f3e8ff")
    author = Column(String(100), default="Admin")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    user = Column(String(100), nullable=False)
    action = Column(String(100), nullable=False)
    details = Column(Text, nullable=True)
    ip_address = Column(String(50), nullable=True)
    type = Column(String(50), default="User Action")

class PermissionSetting(Base):
    __tablename__ = "permission_settings"

    id = Column(Integer, primary_key=True, index=True)
    module_key = Column(String(50), nullable=False, unique=True)
    module_name = Column(String(150), nullable=False)
    admin_access = Column(Integer, default=1)
    de_access = Column(Integer, default=1)
    da_access = Column(Integer, default=1)
    om_access = Column(Integer, default=1)
    viewer_access = Column(Integer, default=0)

# --- 2. Core Data Tables for Pipeline Sync & Ingestion ---
class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String(50), nullable=False, unique=True, index=True)
    name = Column(String(200), nullable=False)
    category = Column(String(100), default="General")
    unit = Column(String(20), default="Units")
    unit_cost = Column(Float, nullable=False, default=0.0)
    selling_price = Column(Float, nullable=False, default=0.0)
    lead_time_days = Column(Integer, nullable=False, default=7)
    safety_stock_min = Column(Integer, nullable=False, default=10)
    reorder_point = Column(Integer, nullable=False, default=20)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    customer_code = Column(String(50), nullable=False, unique=True, index=True)
    name = Column(String(150), nullable=False)
    email = Column(String(100), nullable=True)
    tier = Column(String(20), default="STANDARD")
    created_at = Column(DateTime, default=datetime.utcnow)

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    order_number = Column(String(50), nullable=False, unique=True, index=True)
    customer_id = Column(Integer, nullable=True)
    warehouse_id = Column(Integer, nullable=True)
    order_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    status = Column(String(50), default="PENDING")
    total_amount = Column(Float, default=0.0)
    shipping_address = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Inventory(Base):
    __tablename__ = "inventory"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, nullable=False)
    warehouse_id = Column(Integer, nullable=True, default=1)
    current_stock = Column(Integer, nullable=False, default=0)
    reserved_stock = Column(Integer, default=0)
    in_transit_stock = Column(Integer, default=0)
    reorder_quantity = Column(Integer, default=50)
    last_restock_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Shipment(Base):
    __tablename__ = "shipments"

    id = Column(Integer, primary_key=True, index=True)
    tracking_number = Column(String(100), nullable=False, unique=True, index=True)
    order_id = Column(Integer, nullable=True)
    warehouse_id = Column(Integer, nullable=True)
    carrier = Column(String(100), default="Standard Express")
    status = Column(String(50), default="IN_TRANSIT")
    shipped_date = Column(DateTime, default=datetime.utcnow)
    estimated_delivery = Column(DateTime, nullable=True)
