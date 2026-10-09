"""
Lumen AI Server Launcher (Alias to backend.main)
"""
import uvicorn
from backend.main import app
from backend.config import settings

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host=settings.HOST, port=settings.PORT, reload=False)
