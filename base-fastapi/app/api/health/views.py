from fastapi import APIRouter

from core.schemas.server.response import ApiResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_class=ApiResponse)
async def health_check() -> ApiResponse:
    return ApiResponse(message="OK", data={"status": "healthy"})
