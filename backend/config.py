import os
from typing import List
from dotenv import load_dotenv

# Load .env file from root directory
load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class Settings:
    PROJECT_NAME: str = "Lumen AI — Multilingual Tutor & Adaptive Assistant"
    VERSION: str = "3.0.0"
    API_PREFIX: str = "/api"
    
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", 8000))
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    
    # Gemini Configuration
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    
    # Models for Free vs Plus
    FREE_MODELS: List[str] = [
        "gemini-flash-lite-latest",
        "gemini-flash-latest"
    ]
    PLUS_MODELS: List[str] = [
        "gemini-flash-latest",
        "gemini-3.8-flash",
        "gemini-flash-lite-latest"
    ]
    CANDIDATE_MODELS: List[str] = [
        "gemini-flash-lite-latest",
        "gemini-flash-latest",
        "gemini-3.8-flash"
    ]
    
    # Database and uploads
    DATABASE_PATH: str = os.path.join(BASE_DIR, "lumen.db")
    UPLOADS_DIR: str = os.path.join(BASE_DIR, "uploads")
    SCREENSHOTS_DIR: str = os.path.join(BASE_DIR, "uploads", "screenshots")
    
    # Security & Auth
    SECRET_KEY: str = os.getenv("SECRET_KEY", "lumen-secure-auth-secret-key-2026-v3")
    SESSION_TTL_SECONDS: int = 30 * 24 * 3600  # 30 days
    
    # Initial Admin Configuration
    ADMIN_EMAIL: str = os.getenv("ADMIN_EMAIL", "admin@lumen.ai").lower()
    ADMIN_DEFAULT_PASSWORD: str = os.getenv("ADMIN_DEFAULT_PASSWORD", "Admin@Lumen2026!")
    
    # Plan Limits
    PLUS_PRICE_INR: int = 699
    FREE_MESSAGE_LIMIT: int = 35
    FREE_WINDOW_HOURS: int = 3
    
    # Context window & session limits
    MAX_STORED_SESSIONS: int = 1000
    MAX_CONVERSATION_HISTORY: int = 24
    FREE_CONTEXT_TURNS: int = 8
    PLUS_CONTEXT_TURNS: int = 24
    FREE_HISTORY_TURNS: int = 8
    PLUS_HISTORY_TURNS: int = 24

settings = Settings()
os.makedirs(settings.SCREENSHOTS_DIR, exist_ok=True)
