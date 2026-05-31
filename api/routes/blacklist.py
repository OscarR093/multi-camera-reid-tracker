from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from api.auth import get_current_user, require_admin

router = APIRouter(prefix="/api/blacklist", tags=["blacklist"])


class BlacklistCreate(BaseModel):
    global_id: Optional[str] = None
    description: Optional[str] = None
    reason: Optional[str] = None


@router.get("")
async def list_blacklist(
    active_only: bool = True,
    user: dict = Depends(get_current_user),
):
    from core.pipeline import get_pipeline

    pipeline = get_pipeline()
    if pipeline and pipeline.identity_manager:
        entries = pipeline.identity_manager.sqlite.get_blacklist(
            active_only=active_only
        )
        return {"blacklist": entries}
    return {"blacklist": []}


@router.post("")
async def add_to_blacklist(
    entry: BlacklistCreate,
    admin: dict = Depends(require_admin),
):
    from core.pipeline import get_pipeline

    pipeline = get_pipeline()
    if pipeline and pipeline.identity_manager:
        entry_id = pipeline.identity_manager.sqlite.add_blacklist_entry(
            global_id=entry.global_id,
            description=entry.description,
            reason=entry.reason,
        )
        return {"id": entry_id, "message": "Entry added to blacklist"}
    raise HTTPException(status_code=500, detail="Pipeline not available")


@router.delete("/{entry_id}")
async def remove_from_blacklist(
    entry_id: int,
    admin: dict = Depends(require_admin),
):
    from core.pipeline import get_pipeline

    pipeline = get_pipeline()
    if pipeline and pipeline.identity_manager:
        pipeline.identity_manager.sqlite.deactivate_blacklist_entry(entry_id)
        return {"message": "Entry deactivated"}
    raise HTTPException(status_code=500, detail="Pipeline not available")
