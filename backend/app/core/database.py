from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from backend.app.core.config import settings

# Handle SQLite vs Postgres engine configuration
db_url = settings.DATABASE_URL
if db_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
    engine = create_engine(db_url, connect_args=connect_args, echo=False)
else:
    # Convert postgresql+asyncpg to standard sync postgresql if using sync session, or standard pool
    if "+asyncpg" in db_url:
        sync_url = db_url.replace("+asyncpg", "")
    else:
        sync_url = db_url
    engine = create_engine(sync_url, echo=False, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
