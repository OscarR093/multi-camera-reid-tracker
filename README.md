# Camera Person Counting System

Real-time multi-camera person detection, tracking and counting. YOLOv8n + ByteTrack + ONNX ReID (MobileNetV3). GPU-accelerated via CUDA. Designed for commercial spaces (malls, plazas) as an approximate population sampling system.

<p align="center">
  <img src="screenshots/live-view.png" width="49%" alt="Live camera view with bounding boxes" />
  <img src="screenshots/dashboard.png" width="49%" alt="Dashboard with real-time counts and charts" />
</p>

| | CPU | GPU (RTX 5060 Ti) |
|---|---|---|
| YOLOv8n + ByteTrack | ~30-50 ms/frame | **9.8 ms** |
| ReID embedding (batch) | ~2-3 ms | **2.3 ms** |
| Total per frame | ~40 ms (~~25 FPS) | **~12 ms (~83 FPS)** |
| CPU usage (2 cams @ 5fps) | 40-50% | **<10%** |

## Features

- **Person detection**: YOLOv8n via ultralytics — GPU-accelerated (CUDA)
- **Per-camera tracking**: ByteTrack (ultralytics built-in)
- **Cross-camera re-identification**: MobileNetV3 ONNX embeddings (cosine similarity), GPU via `onnxruntime-gpu`
- **Global identity management**: Redis with configurable TTL (default 10 minutes)
- **MJPEG video stream**: bounding boxes and IDs drawn server-side
- **Dashboard**: React frontend with real-time counts, historical charts, WebSocket updates
- **Authentication**: JWT + bcrypt (admin/viewer roles)
- **Blacklist**: SQLite-backed for flagging persons of interest
- **User management**: CRUD via Admin panel

## Quick start

```bash
# 1. Start Redis
docker compose up -d

# 2. Install GPU dependencies (conda env recommended)
conda activate cameras
pip install onnxruntime-gpu>=1.15.0
conda install -c conda-forge libcublas=12.4 libcufft libcurand libcusolver libcusparse cuda-version=12 cudnn

# 3. Export ONNX ReID model (one-time)
python scripts/export_reid_onnx.py

# 4. Start backend (uses GPU by default)
python main.py

# 5. Start frontend (separate terminal)
cd frontend && npm run dev

# 6. Open http://localhost:5173
#    Login: admin / admin123
```

## Hardware requirements

| Setup | Inference | Cameras | Performance |
|---|---|---|---|
| CPU only (Ryzen 7900, 12c/24t) | CPU | 1-2 @ 5fps | 40-50% CPU usage |
| GPU (RTX 3060+) | CUDA | 10+ @ full rate | CPU mostly idle |
| GPU (RTX 5060 Ti, 16 GB) | CUDA | **Tested**: 2 @ 5fps → **<10% CPU** |

- **YOLOv8n**: ~9.8 ms/frame on GPU (3-5x faster than CPU)
- **ONNX ReID**: ~0.5 ms/inference on GPU (batch of 5 crops: ~2.3 ms)
- **VRAM usage**: ~1.5 GB total (YOLOv8n + ONNX ReID)
- GPU leaves headroom for future face recognition and additional cameras

## Configuration

Copy `.env.example` to `.env` and adjust:

| Variable | Default | Description |
|---|---|---|
| `CAMERA_SOURCES` | `example/CCTV_example.mp4` | Comma-separated video paths or RTSP URLs |
| `IDENTITY_TTL` | `600` | Seconds before an unseen identity expires |
| `HSV_MATCH_THRESHOLD` | `0.7` | Min cosine similarity for ReID match |
| `HEIGHT_MATCH_THRESHOLD` | `0.15` | Max height difference ratio for match |
| `DETECTION_CONFIDENCE` | `0.5` | YOLO confidence threshold |
| `REDIS_HOST` | `localhost` | Redis connection |
| `JWT_SECRET` | (change me) | JWT signing key — change in production |
| `SQLITE_DB_PATH` | `data/persons.db` | SQLite database path |

## Architecture

```
┌─────────────┐
│  RTSP/Videos │────► CameraReader (per camera)
└─────────────┘           │
                          ▼
                   YOLOv8n + ByteTrack ── GPU (CUDA) ──┐
                          │                             │
                   ┌──────┴──────┐                      │
                   ▼              ▼                      │
            bounding boxes    person crops               │
                   │              │                      │
                   │         ONNX ReID ── GPU ──────────┘
                   │         (MobileNetV3)
                   │         1024-dim embedding
                   │              │
                   ▼              ▼
               Identity Manager ◄──┘
               ├─ Cosine similarity > 0.7
               ├─ Height comparison < 15%
               ├─ Redis (global_id, TTL 600s)
               └─ SQLite (events, users, hourly_counts)
                    │
               WebSocket ─► React Frontend

GPU acceleration: YOLOv8n + ByteTrack (PyTorch CUDA) + ReID embedder (ONNX CUDAExecutionProvider)
```

## API

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/api/health` | No | Health check |
| `GET` | `/api/count` | Yes | Current person count |
| `GET` | `/api/count/history?hours=24` | Yes | Hourly historical counts |
| `GET` | `/api/cameras` | Yes | Camera status and active tracks |
| `GET` | `/api/cameras/{id}/mjpeg` | No | MJPEG stream with bounding boxes |
| `GET` | `/api/identities` | Yes | Active global identities |
| `GET` | `/api/events?camera_id=X` | Yes | Event log (enter/exit/heartbeat) |
| `GET` | `/api/blacklist` | Yes | List blacklist entries |
| `POST` | `/api/blacklist` | Admin | Add to blacklist |
| `DELETE` | `/api/blacklist/{id}` | Admin | Deactivate blacklist entry |
| `POST` | `/api/auth/login` | No | Get JWT token (form data) |
| `POST` | `/api/auth/register` | Admin | Create user |
| `GET` | `/api/auth/users` | Admin | List users |
| `WS` | `/ws` | No | Real-time tracking updates |

## Dashboard pages

| Route | Content |
|---|---|
| `/` | Live camera grid with bounding boxes overlay |
| `/dashboard` | Afluency metrics: total persons, cameras online, active tracks, hourly chart |
| `/blacklist` | CRUD for flagged persons |
| `/admin` | User creation and management |

## Testing

```bash
# Test config
python -c "from core.config import settings; print(settings.camera_list)"

# Verify GPU detection
python -c "import torch; print('CUDA:', torch.cuda.is_available()); import onnxruntime as ort; print('ONNX providers:', ort.get_available_providers())"

# Generate fake historical data for dashboard
python scripts/backfill_counts.py

# Clean Redis
docker exec -it camera-redis redis-cli FLUSHDB

# TypeScript check
cd frontend && npx tsc --noEmit

# Production build
cd frontend && npm run build
```

## Docker (GPU)

```bash
# Build and start with GPU access
docker compose up --build -d
```

Requires `nvidia-container-toolkit` on the host. The `docker-compose.yml` includes `deploy.resources.reservations.devices` for GPU passthrough. Dockerfile uses `nvidia/cuda:12.4.1-cudnn-runtime-ubuntu22.04` base image with PyTorch cu124 pre-installed.

## Frontend tech stack

- React 18 + TypeScript
- Vite (dev server + build)
- TailwindCSS (styling)
- Recharts (charts)
- React Router (navigation)
- WebSocket (real-time updates)

## Limitations

- **Angle-dependent ReID**: Cross-camera matching degrades with very different camera angles (same person front vs side view). ONNX ReID is more robust than HSV but not perfect.
- **Crowded scenes**: YOLOv8n and ByteTrack struggle with heavy occlusions (>15 simultaneous people).
- **Approximate counting**: TTL-based expiry means exits are inferred, not directly detected. Suitable for population sampling (±10%), not for exact headcounts.
- **GPU required**: YOLO + ReID now default to CUDA. For CPU-only usage, edit `detector/tracker.py` and `reid/embedder.py` device defaults back to `"cpu"` and use `onnxruntime` (non-gpu).

## Roadmap

- [x] GPU migration (YOLO + ONNX ReID on CUDA)
- [ ] Face recognition for blacklist matching (ArcFace/MobileFaceNet ONNX)
- [ ] Multi-angle ReID robustness improvements
- [ ] Docker GPU deployment automation

## License

Proprietary. All rights reserved.
