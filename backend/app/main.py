"""FastAPI application entry point for Cognivault."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.health import router as health_router
from app.api.router import router as api_router
from app.core.config import Settings
from app.db.database import initialize_database


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the Cognivault API application."""

    resolved_settings = settings or Settings.from_environment()

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        initialize_database(resolved_settings.database_path)
        yield

    application = FastAPI(
        title="Cognivault API",
        description="Backend API for the Cognivault sovereign AI workbench.",
        version="4.0.0",
        lifespan=lifespan,
    )
    application.state.settings = resolved_settings

    application.include_router(health_router)
    application.include_router(api_router)
    return application


app = create_app()
