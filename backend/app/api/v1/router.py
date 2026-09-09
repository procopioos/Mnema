from fastapi import APIRouter

from app.api.v1 import admin, auth, documents, folders, health, setup, tags, workspaces

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(setup.router, tags=["setup"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(workspaces.router, prefix="/workspaces", tags=["workspaces"])
api_router.include_router(documents.router, tags=["documents"])
api_router.include_router(folders.router, tags=["folders"])
api_router.include_router(tags.router, tags=["tags"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
