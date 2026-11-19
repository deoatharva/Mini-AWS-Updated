from fastapi import APIRouter

from app.api.v1 import (
    applications,
    auth,
    compute,
    dashboard,
    databases,
    health,
    iam,
    storage,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(dashboard.router)
api_router.include_router(compute.router)
api_router.include_router(applications.router)
api_router.include_router(storage.router)
api_router.include_router(databases.router)
api_router.include_router(iam.router)
