"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.api import auth, sessions, trends, profile, reports
from app.api.websocket import router as ws_router

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create all DB tables on startup (works for both SQLite and PostgreSQL)."""
    from app.db.base import engine, Base
    # Import models so SQLAlchemy registers them before create_all
    import app.models.user      # noqa
    import app.models.session   # noqa
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# REST routes
app.include_router(auth.router, prefix="/api")
app.include_router(sessions.router, prefix="/api")
app.include_router(trends.router, prefix="/api")
app.include_router(profile.router, prefix="/api")
app.include_router(reports.router, prefix="/api")

# WebSocket route (no /api prefix — ws:// scheme)
app.include_router(ws_router)


@app.get("/api/health")
async def health():
    return {"status": "ok", "app": settings.APP_NAME, "version": settings.APP_VERSION}
