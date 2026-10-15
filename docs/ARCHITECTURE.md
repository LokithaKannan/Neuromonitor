# Architecture — Neurological Monitoring System

## Overview

```
Browser (React + Vite)
        │
        ├─ REST API (axios) ──────────────────────────────────────────┐
        │                                                              │
        └─ WebSocket (native WS / reconnecting-websocket)             │
                │                                                       │
                ▼                                                       │
    FastAPI (Python 3.11+, Uvicorn)                                    │
        │                                                              │
        ├─ /api/auth/*          JWT authentication                    │
        ├─ /api/sessions/*      Session CRUD                          │
        ├─ /api/history/*       Session history                       │
        ├─ /api/trends/*        Longitudinal analytics                │
        ├─ /api/reports/*       PDF/CSV export                        │
        ├─ /api/profile/*       User profile                          │
        │                                                              │
        └─ /ws/monitoring/{session_id}   ◄── WebSocket endpoint       │
                │                                                       │
                ▼                                                       │
    Monitoring Dispatcher (monitoring_service.py)                      │
        │                                                              │
        ├─ TremorService        ← refactored tremor_det.py            │
        ├─ BlinkService         ← refactored blink_detector.py        │
        ├─ AsymmetryService     ← refactored facial_asymmetry.py      │
        └─ PtosisService        ← refactored ptosis_detector.py       │
                │                                                       │
                ▼                                                       │
    SQLAlchemy ORM ──────────────────────────────────────────────────►│
        │                                                     PostgreSQL│
        └─ Alembic migrations                                          │
```

## Data Flow — Real-Time Monitoring

```
1. User clicks "Start Monitoring" in React
2. React opens WebSocket: ws://backend/ws/monitoring/{session_id}
3. Browser captures webcam frame (via canvas.toDataURL / ImageCapture)
4. React sends JSON message:
   { "type": "frame", "data": "<base64 JPEG>", "modules": ["tremor"] }
5. FastAPI WebSocket handler:
   a. Decode base64 → numpy array (cv2.imdecode)
   b. Route to appropriate service(s)
   c. Service processes frame → returns metrics dict
   d. Results serialised → sent back as JSON:
      { "type": "result", "module": "tremor", "data": {...}, "timestamp": ... }
6. React receives result → updates live charts + metrics display
7. Results are buffered; significant results saved to PostgreSQL
8. On session end:
   a. React sends { "type": "stop" }
   b. Backend finalises session, computes summary, saves to DB
   c. Returns session_id → React navigates to results page
```

## Frame Sending Strategy
- React captures frames at ~10 fps (configurable, not every display frame)
- Frames sent as base64 JPEG at ~60% quality to reduce payload size
- Backend decodes and processes; returns only metrics (not video)
- This avoids storing webcam footage in the database

## Module Refactoring Strategy

Each original script is refactored into a stateful service class:

```python
class TremorService:
    def __init__(self): ...        # initialise MediaPipe, deques
    def process_frame(self, frame: np.ndarray) -> dict: ...
    def reset(self): ...           # clear state between sessions
    def get_summary(self) -> dict: ...

class BlinkService:
    def __init__(self): ...
    def process_frame(self, frame: np.ndarray) -> dict: ...
    def reset(self): ...
    def get_summary(self) -> dict: ...

# Same pattern for AsymmetryService, PtosisService
```

Each service:
- Owns its MediaPipe model instance
- Maintains all deques / calibration state
- Exposes `process_frame(frame)` → pure metrics dict (no cv2.imshow, no VideoCapture)
- Exposes `get_summary()` for end-of-session aggregation

## Database Schema

```
users
  id, email, full_name, hashed_password, created_at, is_active

monitoring_sessions
  id, user_id (FK), assessment_type, status, started_at, ended_at, duration_seconds, notes

tremor_results
  id, session_id (FK), timestamp, frequency_hz, amplitude_px, severity, hand_detected

blink_results
  id, session_id (FK), timestamp, ear, ear_threshold, blink_count, blink_rate,
  blink_in_progress, last_blink_duration, face_detected

asymmetry_results
  id, session_id (FK), timestamp, asym_score, eye_asym, mouth_asym, brow_asym,
  asym_event_active, face_detected

ptosis_results
  id, session_id (FK), timestamp, left_ratio, right_ratio, base_left, base_right,
  left_drop, right_drop, ptosis_detected, face_detected

reports
  id, session_id (FK), user_id (FK), created_at, file_path, format
```

## Frontend Structure

```
frontend/
  src/
    api/           client.js + per-module API functions
    components/    reusable UI components
    contexts/      AuthContext, MonitoringContext
    hooks/         useWebSocket, useCamera, useAuth, ...
    pages/
      Landing.jsx
      Login.jsx
      Signup.jsx
      Dashboard.jsx
      NewAssessment.jsx
      Monitoring.jsx
      TremorPage.jsx
      BlinkPage.jsx
      AsymmetryPage.jsx
      PtosisPage.jsx
      CompleteAssessment.jsx
      SessionResults.jsx
      History.jsx
      Trends.jsx
      Reports.jsx
      Profile.jsx
      NotFound.jsx
    styles/        design tokens, global CSS
    utils/
    App.jsx
    main.jsx
```

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, Vite, React Router v6, Recharts, Lucide React |
| Backend | Python 3.11, FastAPI, Uvicorn |
| CV | OpenCV, MediaPipe |
| ORM | SQLAlchemy 2.x (async) |
| Migrations | Alembic |
| Database | PostgreSQL 15+ |
| Auth | JWT (python-jose), bcrypt (passlib) |
| PDF | ReportLab or WeasyPrint |
| WS | FastAPI WebSockets (native) |
| HTTP Client | Axios |

## Security
- Passwords hashed with bcrypt (passlib)
- JWT access tokens (short-lived, 30 min) + refresh tokens
- All routes except /auth/* and /landing require valid JWT
- CORS configured via environment variable ALLOWED_ORIGINS
- SQL injection prevented via SQLAlchemy ORM
- Input validation via Pydantic schemas
- No raw webcam footage stored in DB
