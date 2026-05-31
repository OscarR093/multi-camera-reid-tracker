from fastapi import APIRouter, Depends
from api.auth import get_current_user

router = APIRouter(prefix="/api/identities", tags=["identities"])


@router.get("")
async def list_active_identities(user: dict = Depends(get_current_user)):
    from core.pipeline import get_pipeline

    pipeline = get_pipeline()
    if pipeline and pipeline.identity_manager:
        identities = pipeline.identity_manager.get_active_identities()
        result = []
        for ident in identities:
            result.append(
                {
                    "global_id": ident["global_id"],
                    "last_camera": ident["last_camera"],
                    "last_seen_at": ident["last_seen_at"],
                    "entry_time": ident["entry_time"],
                    "height": ident["height"],
                }
            )
        return {"count": len(result), "identities": result}
    return {"count": 0, "identities": []}
