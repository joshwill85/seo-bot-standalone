"""API v1 router collection."""

from fastapi import APIRouter

from .auth import router as auth_router
from .keywords import router as keywords_router
from .projects import router as projects_router
from .analytics import router as analytics_router

router = APIRouter()

# Include all v1 routers
router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
router.include_router(keywords_router, prefix="/keywords", tags=["Keywords"])
router.include_router(projects_router, prefix="/projects", tags=["Projects"])
router.include_router(analytics_router, prefix="/analytics", tags=["Analytics"])