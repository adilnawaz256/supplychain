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

def add_missing_columns(target_engine):
    """create_all() never alters existing tables, so add columns introduced after first deploy."""
    from sqlalchemy import inspect, text
    added_columns = {
        "workspace_pipeline_configs": {"ingestion_history": "JSON"},
        "sales_history": {"source_key": "VARCHAR(40)"},
        "products": {"subcategory": "VARCHAR(100)", "lead_time_sd_days": "FLOAT", "ordering_cost": "FLOAT",
                     "holding_rate": "FLOAT", "availability_risk": "FLOAT", "supplier_count_risk": "FLOAT",
                     "standardization_risk": "FLOAT", "price_volatility_risk": "FLOAT"},
    }
    inspector = inspect(target_engine)
    for table, cols in added_columns.items():
        if not inspector.has_table(table):
            continue
        existing = {c["name"] for c in inspector.get_columns(table)}
        for col, col_type in cols.items():
            if col not in existing:
                with target_engine.begin() as conn:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}"))
    with target_engine.begin() as conn:
        conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_sales_history_source_key ON sales_history (source_key)"))
