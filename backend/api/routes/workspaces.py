from fastapi import APIRouter, Depends, Body
from sqlalchemy.orm import Session
from typing import Dict, Any

from backend.app.core.database import get_db
from backend.app.models.models import WorkspaceMember

router = APIRouter()

@router.post("/api/workspace/create", tags=["Wisualyst Onboarding"])
def create_workspace(payload: Dict[str, Any] = Body(...)):
    return {
        "status": "SUCCESS",
        "workspace_id": "ws_dubai_retail_01",
        "name": payload.get("name", "Wisualyst Enterprise Workspace"),
        "industry": payload.get("industry", "Retail & Consumer Goods"),
        "region": payload.get("region", "Global / Middle East"),
        "selected_modules": payload.get("modules", ["inventory", "demand", "procurement", "assortment"])
    }

@router.get("/api/workspace/members", tags=["Wisualyst Onboarding"])
def get_workspace_members(db: Session = Depends(get_db)):
    members = db.query(WorkspaceMember).all()
    return [{
        "id": m.id,
        "name": m.name,
        "email": m.email,
        "role": m.role,
        "initials": m.initials,
        "color": m.color,
        "bg": m.bg
    } for m in members]

@router.post("/api/workspace/invite", tags=["Wisualyst Onboarding"])
def invite_workspace_member(payload: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    email = payload.get("email", "")
    name = payload.get("name", email.split("@")[0].title() if "@" in email else "Team Member")
    role = payload.get("role", "Viewer")
    initials = "".join([p[0].upper() for p in name.split()[:2]]) or "U"
    
    new_m = WorkspaceMember(
        name=name,
        email=email,
        role=role,
        initials=initials,
        color="#2563eb",
        bg="#eff6ff"
    )
    db.add(new_m)
    db.commit()
    db.refresh(new_m)
    return {
        "status": "SUCCESS",
        "message": f"Invitation sent to {new_m.email} as {new_m.role}",
        "member": {
            "id": new_m.id,
            "name": new_m.name,
            "email": new_m.email,
            "role": new_m.role,
            "initials": new_m.initials,
            "color": new_m.color,
            "bg": new_m.bg
        }
    }

@router.post("/api/workspace/launch", tags=["Wisualyst Onboarding"])
def launch_workspace():
    return {
        "status": "LAUNCHED",
        "workspace_id": "ws_dubai_retail_01",
        "message": "Workspace successfully configured and launched!"
    }
