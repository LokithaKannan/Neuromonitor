# NeuroMonitor

Real-time neurological monitoring via webcam — detects hand tremor, blink rate, facial asymmetry, and ptosis using computer vision.

Built with **FastAPI**, **React**, **MediaPipe Tasks**, and **SQLite**.

---

## Features

| Module | What it measures |
|---|---|
| **Tremor Detection** | FFT-based hand tremor frequency & amplitude via MediaPipe hand landmarks |
| **Blink Analysis** | Eye Aspect Ratio blink detection with personal baseline calibration |
| **Facial Asymmetry** | Weighted composite score across eye, mouth, and brow disparity |
| **Ptosis Detection** | Eye Opening Ratio per eyelid vs calibrated baseline |

- Live WebSocket stream at ~10 fps
- Session history, trend charts, and PDF report export
- JWT authentication, bcrypt passwords
- Raw video frames are never stored — only computed metrics

---

## Tech Stack

**Backend:** Python 3.11+, FastAPI, SQLAlchemy 2 (async), SQLite / PostgreSQL, Alembic, MediaPipe Tasks, OpenCV, NumPy, ReportLab

**Frontend:** React 19, Vite, React Router, Recharts, Lucide Icons, Axios

---

## Setup

### 1. Clone

```bash
git clone https://github.com/LokithaKannan/Neuromonitor.git
cd Neuromonitor
```

### 2. Backend

```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

**Download MediaPipe model files** (required — not included in the repo):

```bash
# Create models directory
mkdir models

# Hand landmarker (~7.5 MB)
curl -o models/hand_landmarker.task \
  https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task

# Face landmarker (~3.6 MB)
curl -o models/face_landmarker.task \
  https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task
```

**Configure environment:**

```bash
cp .env.example .env
# Edit .env — the defaults work for local SQLite development
```

**Run the server:**

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The database tables are created automatically on first startup.

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**

---

## Environment Variables

Copy `backend/.env.example` to `backend/.env`:

```
DATABASE_URL=sqlite+aiosqlite:///./nms_dev.db
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7
ALLOWED_ORIGINS=http://localhost:5173
```

For PostgreSQL, set `DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/nms_db` and run `alembic upgrade head`.

---

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── api/          # FastAPI routers (auth, sessions, trends, reports, websocket)
│   │   ├── core/         # Config, security (JWT, bcrypt)
│   │   ├── db/           # SQLAlchemy async engine & session
│   │   ├── models/       # SQLAlchemy ORM models
│   │   ├── schemas/      # Pydantic request/response schemas
│   │   ├── services/     # Detection services (tremor, blink, asymmetry, ptosis)
│   │   └── main.py
│   ├── alembic/          # Database migrations
│   ├── models/           # MediaPipe .task model files (download separately)
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/          # Axios API client functions
│   │   ├── components/   # Reusable UI components
│   │   ├── contexts/     # AuthContext
│   │   ├── hooks/        # useCamera, useMonitoringWS
│   │   ├── pages/        # All page components
│   │   └── styles/       # Global CSS & design tokens
│   └── package.json
├── blink_detector.py     # Standalone prototype script
├── facial_asymmetry.py   # Standalone prototype script
└── README.md
```

---

## Notes

- For screening and educational purposes only — not a medical device
- Tested on Python 3.11–3.14 with mediapipe 1.1.1
- MediaPipe model files are excluded from the repo due to size; see setup instructions above
