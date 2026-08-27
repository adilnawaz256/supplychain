import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from backend.app.core.config import settings

db_url = settings.DATABASE_URL or "sqlite:///./supply_chain.db"

# Clean connection parameters that psycopg2 does not accept (like ?pgbouncer=true)
if "?" in db_url and "sqlite" not in db_url:
    base_url, query_params = db_url.split("?", 1)
    params = [p for p in query_params.split("&") if not p.startswith("pgbouncer")]
    db_url = base_url + ("?" + "&".join(params) if params else "")

if db_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
    engine = create_engine(db_url, connect_args=connect_args, echo=False)
else:
    if "+asyncpg" in db_url:
        sync_url = db_url.replace("+asyncpg", "")
    else:
        sync_url = db_url
    try:
        engine = create_engine(sync_url, echo=False, pool_pre_ping=True)
        # Test connection
        with engine.connect() as conn:
            pass
    except Exception as e:
        print(f"Warning: Primary database connection failed ({e}). Falling back to SQLite local database.")
        sqlite_url = "sqlite:///./supply_chain.db"
        connect_args = {"check_same_thread": False}
        engine = create_engine(sqlite_url, connect_args=connect_args, echo=False)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
