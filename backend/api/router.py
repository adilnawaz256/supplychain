"""Wisualyst Central REST API Router.

Consolidates all modular sub-routers into a unified APIRouter.
"""

from fastapi import APIRouter

from backend.api.routes.ml import router as ml_router
from backend.api.routes.catalog import router as catalog_router
from backend.api.routes.control_tower import router as control_tower_router
from backend.api.routes.connectors import router as connectors_router
from backend.api.routes.workspaces import router as workspaces_router
from backend.api.routes.integrations import router as integrations_router
from backend.api.routes.access_control import router as access_control_router
from backend.api.routes.admin import router as admin_router

router = APIRouter()

# Include all modular REST API routers
router.include_router(ml_router)
router.include_router(catalog_router)
router.include_router(control_tower_router)
router.include_router(connectors_router)
router.include_router(workspaces_router)
router.include_router(integrations_router)
router.include_router(access_control_router)
router.include_router(admin_router)
