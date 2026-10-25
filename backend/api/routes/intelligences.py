"""The 9 intelligences on the Intelligence tab. Results are saved like the other ML results and
recalculated after every data import; ?refresh=true recalculates one intelligence now."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.services import snapshots
from backend.ml.intelligences import INTELLIGENCES, compute_intelligence, snapshot_key

router = APIRouter()


@router.get("/api/intelligences", tags=["Intelligences"])
def list_intelligences():
    return [{"id": i, "number": m["number"], "name": m["name"], "question": m["question"], "scopes": m["scopes"]}
            for i, m in INTELLIGENCES.items()]


@router.get("/api/intelligences/{intel_id}", tags=["Intelligences"])
def get_intelligence(intel_id: str, refresh: bool = False, db: Session = Depends(get_db)):
    if intel_id not in INTELLIGENCES:
        raise HTTPException(status_code=404, detail=f"Unknown intelligence '{intel_id}'")
    key = snapshot_key(intel_id)
    if refresh:
        payload, computed_at = snapshots.recompute(db, key)
    else:
        payload, computed_at = snapshots.get_or_compute(db, key)
    return {**payload, "computed_at": computed_at.isoformat() if computed_at else None}
