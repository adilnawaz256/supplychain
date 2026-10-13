from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.services import snapshots

router = APIRouter()

@router.get("/api/control-tower", tags=["Control Tower"])
@router.get("/api/control-tower/summary", tags=["Control Tower"])
def get_control_tower_summary(db: Session = Depends(get_db)):
    return snapshots.get_or_compute(db, "control_tower_summary")[0]

@router.get("/api/recommendations", tags=["Wisualyst Modules"])
def get_unified_recommendations(db: Session = Depends(get_db)):
    return snapshots.get_or_compute(db, "recommendations")[0]
