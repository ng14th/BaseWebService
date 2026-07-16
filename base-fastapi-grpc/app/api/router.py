from fastapi.routing import APIRouter

from app.api.health.views import router as health_router

api_router = APIRouter()
api_router.include_router(health_router, prefix="/v1")
