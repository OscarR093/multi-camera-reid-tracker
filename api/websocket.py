import asyncio
import json
import time
import logging
from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, List, Set
import threading

logger = logging.getLogger(__name__)


class WebSocketManager:
    def __init__(self):
        self._connections: Set[WebSocket] = set()
        self._lock = threading.Lock()
        self._latest_state: Dict = {
            "type": "update",
            "timestamp": time.time(),
            "total_count": 0,
            "cameras": {},
        }

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        with self._lock:
            self._connections.add(websocket)
        logger.info(f"WebSocket client connected ({len(self._connections)} total)")

    async def disconnect(self, websocket: WebSocket):
        with self._lock:
            self._connections.discard(websocket)
        logger.info(f"WebSocket client disconnected ({len(self._connections)} total)")

    async def broadcast(self, message: dict):
        with self._lock:
            connections = set(self._connections)

        disconnected: Set[WebSocket] = set()
        message_json = json.dumps(message, default=str)

        for ws in connections:
            try:
                await ws.send_text(message_json)
            except Exception:
                disconnected.add(ws)

        if disconnected:
            with self._lock:
                self._connections -= disconnected

    def update_camera_state(
        self,
        camera_id: str,
        track_data: list,
        count: int,
    ):
        self._latest_state["cameras"][camera_id] = {
            "count": count,
            "tracks": track_data,
        }
        self._latest_state["timestamp"] = time.time()

    def get_latest_state(self) -> dict:
        return self._latest_state

    def pipeline_callback(self, camera_id: str, track_data: list, count: int):
        self.update_camera_state(camera_id, track_data, count)

    def _update_total_count(self):
        from core.pipeline import get_pipeline
        pipeline = get_pipeline()
        if pipeline and pipeline.identity_manager:
            self._latest_state["total_count"] = pipeline.identity_manager.get_active_count()

    async def broadcast_loop(self, interval: float = 0.5):
        while True:
            await asyncio.sleep(interval)
            if self._connections:
                self._update_total_count()
                await self.broadcast(self.get_latest_state())


ws_manager = WebSocketManager()
