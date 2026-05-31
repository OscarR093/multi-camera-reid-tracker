from fastapi import APIRouter, Depends, Query
from typing import Optional
from api.auth import get_current_user

router = APIRouter(prefix="/api/events", tags=["events"])


@router.get("")
async def list_events(
    camera_id: Optional[str] = None,
    limit: int = Query(default=100, le=1000),
    offset: int = Query(default=0, ge=0),
    user: dict = Depends(get_current_user),
):
    from core.pipeline import get_pipeline

    pipeline = get_pipeline()
    if pipeline and pipeline.identity_manager:
        events = pipeline.identity_manager.sqlite.get_events(
            camera_id=camera_id, limit=limit, offset=offset
        )
        clean_events = []
        for evt in events:
            clean_events.append(
                {
                    k: v
                    for k, v in evt.items()
                    if k != "embedding"
                }
            )
        return {"events": clean_events}
    return {"events": []}
