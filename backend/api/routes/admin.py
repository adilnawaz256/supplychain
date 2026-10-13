from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.core.database import get_db, engine, Base

router = APIRouter()

@router.post("/api/database/clean", tags=["Admin"])
def clean_database(db: Session = Depends(get_db)):
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    return {"status": "SUCCESS", "message": "Database completely cleaned for a new fresh workspace!"}

