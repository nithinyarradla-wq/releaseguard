"""Health check endpoints."""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "healthy", "service": "releaseguard"}


@router.get("/")
def root() -> dict:
    """Root endpoint."""
    return {
        "service": "ReleaseGuard",
        "version": "0.1.0",
        "description": "Automated Release Quality Gate Platform",
        "docs": "/docs",
    }
