import asyncio
import cv2
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from api.websocket import ws_manager
from api.auth import get_current_user

router = APIRouter(prefix="/api/cameras", tags=["cameras"])


@router.get("")
async def list_cameras(user: dict = Depends(get_current_user)):
    state = ws_manager.get_latest_state()
    cameras = {}

    for cam_id, data in state.get("cameras", {}).items():
        cameras[cam_id] = {
            "count": data.get("count", 0),
            "tracks": data.get("tracks", []),
        }

    return {"cameras": cameras}


def draw_bboxes(frame, tracks):
    for track in tracks:
        bbox = track["bbox"]
        x1, y1, x2, y2 = map(int, bbox)
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        short_global = track.get("global_id", "?")[:8] if track.get("global_id") else "?"
        label = f"T{track['local_track_id']} G:{short_global}"
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
        cv2.rectangle(frame, (x1, y1 - th - 8), (x1 + tw + 6, y1 - 2), (0, 0, 0), -1)
        cv2.putText(frame, label, (x1 + 3, y1 - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

    return frame


async def mjpeg_generator(camera_id: str):
    from core.pipeline import get_pipeline

    while True:
        pipeline = get_pipeline()
        if pipeline:
            latest = pipeline.get_latest_frame(camera_id)
            if latest is not None:
                frame, tracks = latest
                frame = draw_bboxes(frame, tracks)
                _, jpeg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" + jpeg.tobytes() + b"\r\n"
                )
        await asyncio.sleep(0.04)


@router.get("/{camera_id}/mjpeg")
async def camera_mjpeg_stream(camera_id: str):
    return StreamingResponse(
        mjpeg_generator(camera_id),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )
