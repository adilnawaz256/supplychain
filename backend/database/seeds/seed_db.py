import hashlib
import secrets
from datetime import datetime
from sqlalchemy.orm import Session

from backend.app.core.database import engine, Base, SessionLocal
from backend.app.models.models import (
    User, Role, WorkspaceMember, PermissionSetting, AuditLog
)

def hash_password(password: str, salt: str = None) -> str:
    if not salt:
        salt = secrets.token_hex(16)
    hashed = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000
    ).hex()
    return f"{salt}${hashed}"

def seed_database(db: Session):
    print("Initializing Clean Auth & Team Database Tables...")
    target_engine = db.bind if (db is not None and db.bind is not None) else engine
    try:
        with target_engine.connect() as conn:
            with conn.begin():
                Base.metadata.drop_all(bind=conn)
                Base.metadata.create_all(bind=conn)
    except Exception as e:
        print(f"Re-creating tables fallback: {e}")
        with target_engine.connect() as conn:
            with conn.begin():
                Base.metadata.create_all(bind=conn)

    print("Database tables created.")

    # 1. Seed Roles
    print("Seeding Roles...")
    roles_seed = [
        ("admin", "Admin", "Full access to all features, settings, data pipelines, and user management.", "Full Access", "#7c3aed", "#f5f3ff"),
        ("de", "Data Engineer", "Manage data sources, database connectors, canonical mappings, and ETL discovery.", "Data & Engine Access", "#2563eb", "#eff6ff"),
        ("da", "Data Analyst", "Analyze inventory metrics, demand forecasts, create custom BI reports, and view insights.", "Read & Analyze", "#059669", "#ecfdf5"),
        ("om", "Operations Manager", "Monitor stockout KPIs, manage alerts, approve PO recommendations, and execute orders.", "Limited Access", "#d97706", "#fffbeb"),
        ("viewer", "Viewer", "View dashboards, alerts, and executive reports with read-only permissions.", "Read Only", "#475569", "#f1f5f9")
    ]
    for r_key, r_name, r_desc, r_scope, r_color, r_bg in roles_seed:
        db.add(Role(role_key=r_key, name=r_name, description=r_desc, scope=r_scope, scope_color=r_color, scope_bg=r_bg, author="System"))
    db.commit()

    # 2. Seed Default Admin User
    print("Seeding Default User...")
    admin_user = User(
        email="admin@supplychain.internal",
        password_hash=hash_password("admin123"),
        full_name="System Administrator",
        company_name="Global Supply Chain Co.",
        role="Admin"
    )
    db.add(admin_user)
    db.commit()

    # 3. Seed Workspace Members
    print("Seeding Workspace Members...")
    members_seed = [
        ("System Administrator", "admin@supplychain.internal", "Admin", "Active", "SA", "#7c3aed", "#f5f3ff"),
        ("Lead Data Engineer", "de@supplychain.internal", "Data Engineer", "Active", "DE", "#2563eb", "#eff6ff"),
        ("Senior Data Analyst", "da@supplychain.internal", "Data Analyst", "Active", "DA", "#059669", "#ecfdf5"),
        ("Operations Manager", "om@supplychain.internal", "Operations Manager", "Active", "OM", "#d97706", "#fffbeb"),
        ("System Viewer", "viewer@supplychain.internal", "Viewer", "Inactive", "SV", "#64748b", "#f1f5f9")
    ]
    for m_name, m_email, m_role, m_status, m_init, m_color, m_bg in members_seed:
        db.add(WorkspaceMember(name=m_name, email=m_email, role=m_role, status=m_status, initials=m_init, color=m_color, bg=m_bg))
    db.commit()

    # 4. Seed Permissions Settings
    print("Seeding Permissions...")
    perms_seed = [
        ("overview", "Overview & Executive Control Tower", 1, 1, 1, 1, 1),
        ("workspaces", "Workspaces & Multi-Tenant Setup", 1, 1, 0, 0, 0),
        ("datasources", "Data Sources & Pipeline", 1, 1, 0, 0, 0),
        ("intelligence", "Intelligence & Forecasting Engines", 1, 1, 1, 1, 1),
        ("recommendations", "Prescriptive Recommendations & PO Dispatch", 1, 0, 1, 1, 0),
        ("access_control", "Access Control & Security Governance", 1, 0, 0, 0, 0)
    ]
    for p_key, p_name, p_admin, p_de, p_da, p_om, p_view in perms_seed:
        db.add(PermissionSetting(module_key=p_key, module_name=p_name, admin_access=p_admin, de_access=p_de, da_access=p_da, om_access=p_om, viewer_access=p_view))
    db.commit()

    # 5. Seed Audit Logs
    print("Seeding Audit Logs...")
    logs_seed = [
        ("System Administrator", "admin@supplychain.internal", "Database Initialized", "System", "Initialized clean database schema", "127.0.0.1"),
        ("System Administrator", "admin@supplychain.internal", "User Login", "Authentication", "User signed into Supply Chain Control Tower", "127.0.0.1")
    ]
    for l_user, l_email, l_act, l_cat, l_det, l_ip in logs_seed:
        db.add(AuditLog(user=l_user, action=l_act, type=l_cat, details=l_det, ip_address=l_ip))
    db.commit()

    print("✅ Clean database seeding completed successfully!")

if __name__ == "__main__":
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()
