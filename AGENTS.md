# AGENTS.md — Camera Person Counting System

## Setup

```bash
# Install Python dependencies (in conda env or venv)
pip install -r requirements.txt

# Install frontend dependencies
cd frontend && npm install
```

## Export ReID model (one-time, or when upgrading model)

```bash
python scripts/export_reid_onnx.py
# → models/reid_mobilenet_v3.onnx (10 MB)
```

This uses MobileNetV3-Small as feature extractor (1024-dim embeddings). The ONNX model runs on CPU via onnxruntime — no GPU required at inference time.

## Run

### With Docker (recommended)

```bash
# Start Redis
docker-compose up -d

# Start frontend dev server
cd frontend && npm run dev
# → http://localhost:5173
```

### Without Docker

Requires Redis running on `localhost:6379`.

```bash
# Terminal 1: Backend
python main.py
# → API at http://localhost:8000

# Terminal 2: Frontend
cd frontend && npm run dev
# → http://localhost:5173
```

## Default credentials

- **Username**: `admin`
- **Password**: `admin123`

## Configuration

Copy `.env.example` to `.env` and adjust:

| Variable | Default | Description |
|---|---|---|
| `CAMERA_SOURCES` | `example/CCTV_example.mp4` | RTSP URLs or local video paths |
| `IDENTITY_TTL` | `600` | Identity expiry in seconds (10 min) |
| `HSV_MATCH_THRESHOLD` | `0.7` | Min cosine similarity for re-identification (ReID model) |
| `HEIGHT_MATCH_THRESHOLD` | `0.15` | Max height difference ratio for re-identification |
| `REDIS_HOST` | `localhost` | Redis host |
| `JWT_SECRET` | `dev-secret-...` | Change in production |

## Commands

```bash
# Backend
python main.py                          # Start backend
python -c "from core.config import settings; print(settings.camera_list)"  # Test config
python scripts/export_reid_onnx.py       # Re-export ONNX model
python scripts/backfill_counts.py        # Generate fake historical data

# Frontend
cd frontend && npm run dev              # Dev server with HMR
cd frontend && npm run build            # Production build
cd frontend && npx tsc --noEmit         # TypeScript type check

# Docker
docker-compose up -d                    # Start Redis
docker-compose down                     # Stop Redis
docker exec -it camera-redis redis-cli  # Access Redis CLI
docker exec -it camera-redis redis-cli FLUSHDB  # Clean all Redis data
```

## API endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/api/health` | No | Health check |
| `GET` | `/api/count` | Yes | Current person count |
| `GET` | `/api/count/history?hours=24` | Yes | Historical counts |
| `GET` | `/api/cameras` | Yes | Camera status + tracks |
| `GET` | `/api/cameras/{cam_id}/mjpeg` | No | MJPEG stream with bounding boxes |
| `GET` | `/api/identities` | Yes | Active global identities |
| `GET` | `/api/events?camera_id=X` | Yes | Event log |
| `GET` | `/api/blacklist` | Yes | List blacklist |
| `POST` | `/api/blacklist` | Admin | Add to blacklist |
| `DELETE` | `/api/blacklist/{id}` | Admin | Deactivate entry |
| `POST` | `/api/auth/login` | No | Login (form data) |
| `POST` | `/api/auth/register` | Admin | Create user |
| `GET` | `/api/auth/users` | Admin | List users |
| `WS` | `/ws` | No | Real-time tracking updates |

## Architecture

```
Video file/RTSP ─► CameraReader ─► YOLOv8n + ByteTrack
                                      │
                                      ▼
                                Person Crop ─► ONNX ReID (MobileNetV3)
                                      │            │
                                      │       1024-dim embedding
                                      ▼
                                 Identity Manager
                                 ├─ Cosine similarity > 0.7
                                 ├─ Height comparison
                                 ├─ Redis (global_id + TTL 600s)
                                 └─ SQLite (events, users, blacklist, hourly_counts)
                                      │
                                 WebSocket ─► Frontend (React)
```

## Testing cross-camera identity matching

Set `CAMERA_SOURCES` to the same video twice:

```
CAMERA_SOURCES=example/test.mp4,example/test.mp4
```

If matching works, the `total_count` badge in the frontend will show ~N (not ~2N). Each bounding box label shows `T{local_id} G:{global_id_prefix}` — the `G:` prefix should match across cameras for the same person.

## Performance notes

- YOLOv8n inference: ~30-50ms per frame per camera on CPU
- ONNX ReID per crop batch: ~2-3ms on CPU
- **Total CPU usage: 40-50% on Ryzen 7900 (12-core) with 2 cameras at ~5fps**
- Production recommendation: cap detection rate at 5fps via `DETECTION_INTERVAL`; use GPU for >2 cameras or >5fps
- For GPU inference, set `device="cuda"` in tracker/embedder init and change `CAMERA_SOURCES` to RTSP URLs
