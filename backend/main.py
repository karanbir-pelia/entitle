import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import chat, eligibility, document
from config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Entitle API",
    description="Safety Net Benefits Navigator powered by Gemma 4",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.frontend_url,
        "http://localhost:5173",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router, prefix="/api")
app.include_router(eligibility.router, prefix="/api")
app.include_router(document.router, prefix="/api")


@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "model_backend": settings.model_backend,
        "model": (
            settings.ollama_model
            if settings.model_backend == "ollama"
            else settings.gemini_model
        ),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.backend_host,
        port=settings.backend_port,
        reload=True,
    )
