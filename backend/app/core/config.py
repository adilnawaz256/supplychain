import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    PROJECT_NAME: str = os.getenv("PROJECT_NAME", "Supply Chain AI Decision-Intelligence")
    PORT: int = int(os.getenv("PORT", "8000"))
    HOST: str = os.getenv("HOST", "0.0.0.0")
    
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://postgres.cugiwyrgfptehvkexejg:StrongPassword%40123..@aws-0-ap-southeast-1.pooler.supabase.com:5432/postgres")
    
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    AI_PROVIDER: str = os.getenv("AI_PROVIDER", "openai").lower() # openai, claude, gemini, rule_based
    
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

settings = Settings()
