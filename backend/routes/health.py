from fastapi import APIRouter
from backend.config import settings

router = APIRouter(prefix="/health", tags=["Health"])

@router.get("")
async def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "models": settings.CANDIDATE_MODELS,
        "api_key_configured": bool(settings.GEMINI_API_KEY)
    }
