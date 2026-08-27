import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from backend.app.core.config import settings

db_url = settings.DATABASE_URL or "postgresql://postgres.cugiwyrgfptehvkexejg:StrongPassword%40123..@aws-0-ap-southeast-1.pooler.supabase.com:5432/postgres"

# Clean connection parameters that psycopg2 does not accept (like ?pgbouncer=true)
if "?" in db_url and "sqlite" not in db_url:
    base_url, query_params = db_url.split("?", 1)
    params = [p for p in query_params.split("&") if not p.startswith("pgbouncer")]
    db_url = base_url + ("?" + "&".join(params) if params else "")

if db_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
    engine = create_engine(db_url, connect_args=connect_args, echo=False)
else:
    sync_url = db_url.replace("+asyncpg", "") if "+asyncpg" in db_url else db_url
    engine = create_engine(sync_url, echo=False, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
