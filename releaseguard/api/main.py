"""FastAPI application entry point."""

from fastapi import FastAPI

from releaseguard.api.routes import releases, health
from releaseguard.db import engine, Base

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="ReleaseGuard",
    description="Automated Release Quality Gate Platform",
    version="0.1.0",
)

# Include routers
app.include_router(health.router)
app.include_router(releases.router)
