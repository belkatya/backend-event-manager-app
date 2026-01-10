# app/main.py
import uvicorn
from config import settings

if __name__ == "__main__":
    uvicorn.run(
        "server.server:app",
        host="127.0.0.1",
        port=8000,
        reload=settings.RELOAD,
        workers=settings.WORKERS,
        log_level="info"
    )