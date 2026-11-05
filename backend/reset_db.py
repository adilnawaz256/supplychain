"""Database Reset Script for Wisualyst Platform.

Drops all existing tables and re-creates clean schema tables.
Can be run on SQLite, PostgreSQL (Supabase / AWS RDS), or MySQL.
"""

import sys
import os

_backend_dir = os.path.dirname(os.path.abspath(__file__))
_root_dir = os.path.dirname(_backend_dir)
for _p in [_backend_dir, _root_dir]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from backend.app.core.database import engine, Base, SessionLocal
from backend.app.models.models import *

def reset_db(seed_initial_data: bool = True):
    print("===================================================")
    print("🧹 Wiping database and creating fresh clean schema...")
    print("===================================================")

    with engine.connect() as conn:
        with conn.begin():
            print("1. Dropping all existing tables...")
            Base.metadata.drop_all(bind=conn)
            print("2. Creating new empty tables...")
            Base.metadata.create_all(bind=conn)

    print("✅ All tables dropped and re-created successfully!")

    if seed_initial_data:
        print("🌱 Seeding initial roles, permissions, and demo data...")
        from backend.database.seeds.seed_db import seed_database
        db = SessionLocal()
        try:
            seed_database(db)
            print("✅ Database seeding complete!")
        finally:
            db.close()

if __name__ == "__main__":
    seed_arg = "--no-seed" not in sys.argv
    reset_db(seed_initial_data=seed_arg)
