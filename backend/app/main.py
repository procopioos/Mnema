from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import health as health_module
from app.api.v1.errors import register_exception_handlers
from app.api.v1.router import api_router
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(title=settings.app_name, version="0.1.0")

register_exception_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")

for path in ("/health", "/api/health", "/api/status"):
    app.add_api_route(path, health_module.health, methods=["GET"], tags=["health"])


@app.get("/")
async def root() -> dict[str, str]:
    return {"name": settings.app_name, "version": "0.1.0", "docs": "/docs"}
