# AGENTS.md — Camera Person Counting System

## Setup

### With GPU (default)

```bash
# Install Python dependencies (conda env recommended)
conda activate cameras
pip install onnxruntime-gpu>=1.15.0

# Install CUDA 12 runtime libraries
conda install -c conda-forge libcublas=12.4 libcufft libcurand libcusolver libcusparse cuda-version=12 cudnn

# Install frontend dependencies
cd frontend && npm install

# Verify GPU
python -c "
import torch; print('CUDA:', torch.cuda.is_available())
import onnxruntime as ort; print('ONNX:', ort.get_available_providers())
"
```

### Without GPU (fallback)

```bash
pip install onnxruntime>=1.15.0  # non-GPU version
```

Then edit `detector/tracker.py` and `reid/embedder.py`: change `device: str = "cuda"` → `device: str = "cpu"`.

## Export ReID model (one-time, or when upgrading model)

```bash
python scripts/export_reid_onnx.py
# → models/reid_mobilenet_v3.onnx (10 MB)
```

This uses MobileNetV3-Small as feature extractor (1024-dim embeddings). The ONNX model runs on GPU via `onnxruntime-gpu` (CUDAExecutionProvider) by default.

## Run

### With Docker (GPU recommended)

```bash
# Build and start backend + Redis with GPU access
docker compose up --build -d
# → API at http://localhost:8000

# Start frontend dev server
cd frontend && npm run dev
# → http://localhost:5173
```

### Without Docker (direct Python)

Requires Redis running on `localhost:6379`.

```bash
# Terminal 1: Start Redis
docker compose up -d redis

# Terminal 2: Backend (GPU by default)
python main.py
# → API at http://localhost:8000

# Terminal 3: Frontend
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
python main.py                          # Start backend (GPU)
python -c "from core.config import settings; print(settings.camera_list)"  # Test config
python scripts/export_reid_onnx.py       # Re-export ONNX model
python scripts/backfill_counts.py        # Generate fake historical data

# GPU verification
python -c "import torch; print('CUDA:', torch.cuda.is_available(), torch.cuda.get_device_name(0))"
python -c "import onnxruntime as ort; print('Providers:', ort.get_available_providers())"

# Frontend
cd frontend && npm run dev              # Dev server with HMR
cd frontend && npm run build            # Production build
cd frontend && npx tsc --noEmit         # TypeScript type check

# Docker
docker compose up --build -d            # Start all services with GPU
docker compose down                     # Stop all services
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
Video file/RTSP ─► CameraReader ─► YOLOv8n + ByteTrack (GPU via CUDA)
                                      │
                                      ▼
                                Person Crop ─► ONNX ReID (GPU via CUDAExecutionProvider)
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

Both inference components (YOLOv8n + ReID embedder) run on GPU by default:
- YOLOv8n uses PyTorch CUDA backend (`device="cuda"`)
- ReID embedder uses `onnxruntime-gpu` with `CUDAExecutionProvider`

## Testing cross-camera identity matching

Set `CAMERA_SOURCES` to the same video twice:

```
CAMERA_SOURCES=example/test.mp4,example/test.mp4
```

If matching works, the `total_count` badge in the frontend will show ~N (not ~2N). Each bounding box label shows `T{local_id} G:{global_id_prefix}` — the `G:` prefix should match across cameras for the same person.

## Performance notes

| Component | CPU (Ryzen 7900) | GPU (RTX 5060 Ti) |
|---|---|---|
| YOLOv8n + ByteTrack | ~30-50 ms/frame | **9.8 ms** |
| ONNX ReID (batch 5) | ~2-3 ms | **2.3 ms** |
| Total per frame | ~40 ms | **~12 ms** |
| Max theoretical FPS | ~25 | **~83** |
| CPU usage (2 cams @ 5fps) | 40-50% | **<10%** |
| VRAM usage | N/A | ~1.5 GB |

- YOLOv8n inference on GPU: **3-5x faster** than CPU
- ONNX ReID on GPU: scales efficiently with batch size
- GPU leaves plenty of headroom for face recognition and additional cameras
- For CPU fallback, change `device="cuda"` → `device="cpu"` in `detector/tracker.py:10` and `reid/embedder.py:14`
