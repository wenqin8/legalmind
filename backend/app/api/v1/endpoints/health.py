"""Public process health endpoint."""

from fastapi import APIRouter, Request

from app import __version__
from app.schemas.common import ApiSuccess
from app.schemas.health import HealthData

router = APIRouter()


@router.get("/health", response_model=ApiSuccess[HealthData])
async def health_check(request: Request) -> ApiSuccess[HealthData]:
    """Report API liveness without probing or exposing dependencies."""

    return ApiSuccess(
        data=HealthData(version=__version__),
        request_id=request.state.request_id,
    )
