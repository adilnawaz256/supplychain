import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from backend.app.core.config import settings

db_url = settings.DATABASE_URL

if db_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
    engine = create_engine(db_url, connect_args=connect_args, echo=False)
else:
    sync_url = db_url.replace("+asyncpg", "") if "+asyncpg" in db_url else db_url
    if "supabase" in sync_url.lower() or "pooler" in sync_url.lower():
        engine = create_engine(
            sync_url,
            echo=False,
            poolclass=NullPool,
            pool_pre_ping=True
        )
    else:
        engine = create_engine(
            sync_url,
            echo=False,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=5,
            pool_recycle=300,
            pool_timeout=10
        )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
