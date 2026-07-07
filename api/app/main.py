"""FastAPI application entry point.

Wires CORS and mounts routers. The LLM/RAG/email machinery arrives in later
phases; Phase 0 exposes only a health check and an authenticated `/me`.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import accounts as accounts_router
from app.routers import documents as documents_router
from app.routers import drafts as drafts_router
from app.routers import emails as emails_router
from app.routers import me as me_router
from app.routers import settings as settings_router

settings = get_settings()

app = FastAPI(
    title="Draftline API",
    version="0.1.0",
    description="AI inbox assistant — read, classify, and draft. Never sends.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    """Liveness probe. Cheap and unauthenticated (used to warm the free tier)."""
    return {"status": "ok"}


app.include_router(me_router.router)
app.include_router(accounts_router.router)
app.include_router(emails_router.router)
app.include_router(settings_router.router)
app.include_router(documents_router.router)
app.include_router(drafts_router.router)
