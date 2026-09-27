from sqlalchemy import Column, Integer, String, DateTime, Text
from datetime import datetime
from backend.app.core.database import Base

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
