from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import logging
import threading

from api.websocket import ws_manager
from api.routes import count, cameras, identities, events, blacklist, auth_routes

logger = logging.getLogger(__name__)

app = FastAPI(title="Person Counting API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(count.router)
app.include_router(cameras.router)
app.include_router(identities.router)
app.include_router(events.router)
app.include_router(blacklist.router)
app.include_router(auth_routes.router)


@app.get("/api/health")
async def health_check():
    return {"status": "ok"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket)


@app.on_event("startup")
async def startup_event():
    logger.info("API starting up")
    asyncio.create_task(ws_manager.broadcast_loop())


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("API shutting down")
