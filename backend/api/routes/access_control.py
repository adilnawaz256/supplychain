from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import Dict, Any

from backend.app.core.database import get_db
from backend.app.models.models import Role, WorkspaceMember, PermissionSetting, AuditLog

router = APIRouter()

@router.get("/api/access-control/roles", tags=["Access Control"])
def get_access_roles(db: Session = Depends(get_db)):
    db_roles = db.query(Role).all()
    if not db_roles:
        init_roles = [
            Role(role_key="admin", name="Admin", description="Full access to all features, settings, and user management.", scope="Full Access", scope_color="#7c3aed", scope_bg="#f3e8ff", author="System"),
            Role(role_key="de", name="Data Engineer", description="Manage data sources, mappings, and intelligence engines.", scope="Data & Engine Access", scope_color="#2563eb", scope_bg="#dbeafe", author="System"),
            Role(role_key="da", name="Data Analyst", description="Analyze data, create reports, and view insights.", scope="Read & Analyze", scope_color="#059669", scope_bg="#d1fae5", author="System"),
            Role(role_key="om", name="Operations Manager", description="Monitor KPIs, manage alerts, and view recommendations.", scope="Limited Access", scope_color="#d97706", scope_bg="#fef3c7", author="System"),
            Role(role_key="viewer", name="Viewer", description="View dashboards and reports with read-only access.", scope="Read Only", scope_color="#475569", scope_bg="#f1f5f9", author="System")
        ]
        db.add_all(init_roles)
        db.commit()
        db_roles = db.query(Role).all()
    
    result = []
    for r in db_roles:
        user_count = db.query(WorkspaceMember).filter(WorkspaceMember.role.ilike(f"%{r.name}%")).count()
        result.append({
            "id": r.role_key,
            "name": r.name,
            "desc": r.description or "",
            "usersCount": user_count,
            "scope": r.scope or "Full Access",
            "scopeColor": r.scope_color or "#7c3aed",
            "scopeBg": r.scope_bg or "#f5f3ff",
            "lastModified": r.updated_at.strftime("%b %d, %Y") if r.updated_at else "Today",
            "author": r.author or "System"
        })
    return result

@router.post("/api/access-control/roles", tags=["Access Control"])
def create_role(payload: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    name = payload.get("name", "Custom Role")
    desc = payload.get("description", "Custom user role")
    role_key = name.lower().replace(" ", "-")
    
    existing = db.query(Role).filter(Role.role_key == role_key).first()
    if existing:
        return {"status": "EXISTS", "message": f"Role '{name}' already exists.", "role": {
            "id": existing.role_key, "name": existing.name, "desc": existing.description, "usersCount": 0
        }}

    new_role = Role(
        role_key=role_key,
        name=name,
        description=desc,
        scope=payload.get("scope", "Custom Scope"),
        scope_color="#2563eb",
        scope_bg="#eff6ff",
        author="Admin"
    )
    db.add(new_role)
    db.commit()
    db.refresh(new_role)
    
    return {
        "status": "SUCCESS",
        "message": f"Role '{name}' created successfully in database!",
        "role": {
            "id": new_role.role_key,
            "name": new_role.name,
            "desc": new_role.description,
            "usersCount": 0,
            "scope": new_role.scope,
            "scopeColor": new_role.scope_color,
            "scopeBg": new_role.scope_bg,
            "lastModified": new_role.updated_at.strftime("%b %d, %Y") if new_role.updated_at else "Today",
            "author": new_role.author
        }
    }

@router.get("/api/access-control/users", tags=["Access Control"])
def get_access_users(db: Session = Depends(get_db)):
    members = db.query(WorkspaceMember).all()
    result = []
    for m in members:
        result.append({
            "id": m.id,
            "name": m.name,
            "email": m.email,
            "role": m.role,
            "roleId": m.role.lower().replace(" ", "-"),
            "status": m.status or "Active",
            "lastActive": "Active Today",
            "avatarBg": m.color or "#2563eb"
        })
    return result

@router.post("/api/access-control/users/invite", tags=["Access Control"])
def invite_user(payload: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    email = payload.get("email", "").strip()
    role = payload.get("role", "Viewer")
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")
        
    name = email.split("@")[0].title().replace(".", " ")
    initials = "".join([part[0] for part in name.split()])[:2].upper()
    
    existing = db.query(WorkspaceMember).filter(WorkspaceMember.email == email).first()
    if existing:
        existing.role = role
        db.commit()
        return {"status": "UPDATED", "message": f"Updated role for {email} to {role}!", "invited_user": {
            "id": existing.id, "name": existing.name, "email": existing.email, "role": existing.role, "status": existing.status
        }}

    new_mem = WorkspaceMember(
        name=name,
        email=email,
        role=role,
        status="Active",
        initials=initials,
        color="#2563eb",
        bg="#eff6ff"
    )
    db.add(new_mem)
    db.commit()
    db.refresh(new_mem)
    
    return {
        "status": "SUCCESS",
        "message": f"Invitation link generated and saved to database for {email} as {role}!",
        "invited_user": {
            "id": new_mem.id,
            "name": new_mem.name,
            "email": new_mem.email,
            "role": new_mem.role,
            "status": new_mem.status,
            "lastActive": "Invited Today",
            "avatarBg": new_mem.color
        }
    }

@router.delete("/api/access-control/users/{user_id}", tags=["Access Control"])
def revoke_user_access(user_id: int, db: Session = Depends(get_db)):
    mem = db.query(WorkspaceMember).filter(WorkspaceMember.id == user_id).first()
    if mem:
        db.delete(mem)
        db.commit()
        return {"status": "SUCCESS", "message": f"User #{user_id} removed from database."}
    return {"status": "NOT_FOUND", "message": "User record not found."}

@router.get("/api/access-control/permissions", tags=["Access Control"])
def get_permissions_matrix(db: Session = Depends(get_db)):
    perms = db.query(PermissionSetting).all()
    if not perms:
        return []
    return [
        {
            "module": p.module_name,
            "key": p.module_key,
            "admin": bool(p.admin_access),
            "data_engineer": bool(p.de_access),
            "data_analyst": bool(p.da_access),
            "ops_manager": bool(p.om_access),
            "viewer": bool(p.viewer_access)
        } for p in perms
    ]

@router.get("/api/access-control/audit-logs", tags=["Access Control"])
def get_audit_logs(db: Session = Depends(get_db)):
    logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).all()
    if not logs:
        return []
    return [
        {
            "id": f"aud-{l.id}",
            "timestamp": l.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC") if l.timestamp else "Just now",
            "user": getattr(l, "user_name", None) or getattr(l, "user", "System Administrator"),
            "email": getattr(l, "user_email", None) or "admin@supplychain.internal",
            "action": l.action,
            "category": getattr(l, "category", None) or getattr(l, "type", "General"),
            "details": l.details or "",
            "ip": l.ip_address or "127.0.0.1",
            "severity": getattr(l, "severity", None) or "INFO"
        } for l in logs
    ]
