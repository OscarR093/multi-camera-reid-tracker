import time
from fastapi import APIRouter, Depends
from api.websocket import ws_manager
from api.auth import get_current_user

router = APIRouter(prefix="/api/count", tags=["count"])


@router.get("")
async def get_current_count(user: dict = Depends(get_current_user)):
    from core.pipeline import get_pipeline

    pipeline = get_pipeline()
    active_identities = 0
    if pipeline and pipeline.identity_manager:
        active_identities = pipeline.identity_manager.get_active_count()

    state = ws_manager.get_latest_state()
    return {
        "total_count": active_identities,
        "cameras": {
            cam_id: {"count": data.get("count", 0)}
            for cam_id, data in state.get("cameras", {}).items()
        },
        "timestamp": state.get("timestamp", time.time()),
    }


@router.get("/history")
async def get_count_history(
    hours: int = 24, user: dict = Depends(get_current_user)
):
    from core.pipeline import get_pipeline

    pipeline = get_pipeline()
    if pipeline and pipeline.identity_manager:
        sqlite = pipeline.identity_manager.sqlite
        data = sqlite.get_hourly_counts(hours)
        return {"hours": hours, "data": data}
    return {"hours": hours, "data": []}
