from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.core.database import get_db, engine, Base
from database.seeds.seed_db import seed_database

router = APIRouter()

@router.post("/api/database/clean", tags=["Admin"])
def clean_database(db: Session = Depends(get_db)):
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    return {"status": "SUCCESS", "message": "Database completely cleaned for a new fresh workspace!"}

@router.post("/api/database/seed", tags=["Admin"])
@router.post("/api/seed-database", tags=["Admin"])
def run_seed_db(db: Session = Depends(get_db)):
    seed_database(db)
    return {"status": "SUCCESS", "message": "Database successfully seeded with realistic supply chain data!"}
