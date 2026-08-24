from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.core.config import settings
from backend.app.core.database import Base, engine, SessionLocal
from backend.app.api.router import router
from database.seeds.seed_db import seed_database
from backend.app.models.models import Product

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Enterprise Supply Chain AI Decision-Intelligence Phase-1 POC API",
    version="1.0.0"
)

# CORS Middleware setup for Frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

@app.on_event("startup")
def startup_event():
    print(f"Starting {settings.PROJECT_NAME} Backend...")
    # Initialize database tables
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        prod_count = db.query(Product).count()
        if prod_count == 0:
            print("Database empty. Auto-seeding initial supply chain data...")
            seed_database(db)
            print("Auto-seeding complete.")
        else:
            print(f"Database contains {prod_count} products.")
    except Exception as e:
        print(f"Startup DB Check Note: {e}")
    finally:
        db.close()

@app.get("/", tags=["Health Check"])
def root():
    return {
        "project": settings.PROJECT_NAME,
        "status": "ONLINE",
        "docs_url": "/docs",
        "environment": settings.ENVIRONMENT
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
