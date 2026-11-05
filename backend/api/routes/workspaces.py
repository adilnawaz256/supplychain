from fastapi import APIRouter, Depends, Body
from sqlalchemy.orm import Session
from typing import Dict, Any

from backend.app.core.database import get_db
from backend.app.models.models import WorkspaceMember, WorkspacePipelineConfig

router = APIRouter()

@router.get("/api/workspace/current", tags=["Wisualyst Onboarding"])
def get_current_workspace(db: Session = Depends(get_db)):
    cfg = db.query(WorkspacePipelineConfig).filter(WorkspacePipelineConfig.workspace_key == "default").first()
    return {
        "status": "SUCCESS",
        "workspace_id": "ws_dubai_retail_01",
        "name": cfg.workspace_name if cfg and cfg.workspace_name else "Global Supply Chain",
        "industry": cfg.industry_vertical if cfg and cfg.industry_vertical else "Retail & Distribution",
        "region": cfg.workspace_region if cfg and cfg.workspace_region else "UAE / GCC Hub",
        "is_connected": bool(cfg and cfg.is_connected)
    }

@router.post("/api/workspace/create", tags=["Wisualyst Onboarding"])
def create_workspace(payload: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    name = payload.get("name", "Global Supply Chain")
    industry = payload.get("industry", "Retail & Distribution")
    region = payload.get("region", "UAE / GCC Hub")
    
    cfg = db.query(WorkspacePipelineConfig).filter(WorkspacePipelineConfig.workspace_key == "default").first()
    if not cfg:
        cfg = WorkspacePipelineConfig(
            workspace_key="default",
            workspace_name=name,
            workspace_region=region,
            industry_vertical=industry
        )
        db.add(cfg)
    else:
        cfg.workspace_name = name
        cfg.workspace_region = region
        cfg.industry_vertical = industry
    db.commit()
    db.refresh(cfg)

    return {
        "status": "SUCCESS",
        "workspace_id": "ws_dubai_retail_01",
        "name": cfg.workspace_name,
        "industry": cfg.industry_vertical,
        "region": cfg.workspace_region,
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
