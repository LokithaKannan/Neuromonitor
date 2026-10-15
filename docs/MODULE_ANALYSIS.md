# Module Analysis — Neurological Monitoring System

## 1. tremor_det.py

### Purpose
Detects hand tremors via webcam by tracking an index-finger tip landmark (MediaPipe landmark #8).
Calculates tremor frequency (Hz) and movement amplitude, then classifies severity.

### Dependencies
- `cv2` (OpenCV)
- `mediapipe` (mp.solutions.hands)
- `numpy`
- `collections.deque`
- `time`, `os`

### Input
- Live webcam frame (BGR numpy array, any resolution)
- MediaPipe hand landmarks (requires a detected hand in frame)

### Output / Metrics
| Metric | Type | Description |
|--------|------|-------------|
| `frequency` | float Hz | Peak frequency from FFT of landmark #8 X+Y position history |
| `amplitude` | float px | Mean frame-to-frame Euclidean distance of landmark #8 |
| `severity` | string | Classification (see below) |
| `hand_detected` | bool | Whether a hand was found in the frame |

### Severity Classification (classify_tremor_severity)
```
frequency < 1 Hz → "No tremor"
1–4 Hz + amp < 2 → "Low-freq mild tremor"
1–4 Hz + amp 2–5 → "Low-freq moderate tremor"
1–4 Hz + amp > 5 → "Low-freq severe tremor"
4–12 Hz + amp < 2 → "Mild physiological tremor"
4–12 Hz + amp 2–5 → "Moderate physiological tremor"
4–12 Hz + amp > 5 → "Severe physiological tremor"
> 12 Hz + amp < 2 → "High-freq mild tremor"
> 12 Hz + amp 2–5 → "High-freq moderate tremor"
> 12 Hz + amp > 5 → "High-freq severe tremor"
```

### Key Constants
- `positions` deque maxlen = 150 (rolling window)
- Minimum 30 positions required for frequency calculation
- FFT frequency range: 0–20 Hz

### Algorithm Flow
1. Flip frame horizontally
2. Convert BGR → RGB
3. Run MediaPipe Hands (max 1 hand, conf 0.6)
4. If hand found → record (x, y, timestamp) of landmark #8
5. If ≥30 samples: compute amplitude + FFT frequency → classify severity
6. Optionally save snapshot images to `tremor_snapshots/`

### Webcam / Desktop Code to Refactor
- `cv2.VideoCapture(0)` → caller provides frames
- `cv2.imshow()` / `cv2.waitKey()` → remove
- `while True:` loop → replace with single-frame process function
- `os.makedirs` / `cv2.imwrite` snapshots → optional, not needed in web

### Reusable Functions
- `classify_tremor_severity(amplitude, frequency)` — pure function, keep as-is
- `calculate_movement_amplitude(positions)` — pure function, keep as-is
- `detect_tremor_frequency(positions)` — pure function, keep as-is

### Expected Web API Output (per frame)
```json
{
  "hand_detected": true,
  "frequency": 4.21,
  "amplitude": 3.10,
  "severity": "Moderate physiological tremor",
  "positions_count": 87
}
```

---

## 2. blink_detector.py

### Purpose
Detects blinks using MediaPipe Face Mesh, computes Eye Aspect Ratio (EAR),
calibrates to each user's open-eye baseline, counts blinks, measures duration,
calculates blink rate, and identifies abnormal blink patterns.

### Dependencies
- `cv2` (OpenCV)
- `mediapipe` (mp.solutions.face_mesh, refine_landmarks=True)
- `numpy`
- `collections.deque`
- `time`, `csv`
- `pandas` (post-session analysis only)
- `matplotlib` (post-session graph only — not needed in web)

### Landmark Indices
```
LEFT_EYE_IDX  = [33, 160, 158, 133, 153, 144]
RIGHT_EYE_IDX = [362, 385, 387, 263, 373, 380]
```

### Constants / Thresholds
| Name | Value | Meaning |
|------|-------|---------|
| CALIBRATION_SECONDS | 2.0 | Seconds to collect baseline EAR |
| SMOOTHING_WINDOW | 3 | Rolling average window for EAR |
| EAR_THRESHOLD_FACTOR | 0.70 | `threshold = baseline * 0.70` |
| MIN_BLINK_DURATION | 0.03 s | Shortest valid blink |
| MAX_BLINK_DURATION | 1.2 s | Longest valid blink |
| FALLBACK_EAR_THRESHOLD | 0.21 | Used if calibration insufficient |
| NORMAL_BLINK_MIN | 0.08 s | Normal blink duration lower bound |
| NORMAL_BLINK_MAX | 0.60 s | Normal blink duration upper bound |
| NORMAL_RATE_MIN | 10 bpm | Lower normal blink rate |
| NORMAL_RATE_MAX | 20 bpm | Upper normal blink rate |

### Input
- Live webcam frame (BGR numpy array)
- Face must be visible for Face Mesh

### Output / Metrics (per frame during monitoring)
| Metric | Type |
|--------|------|
| `ear` | float — current smoothed EAR |
| `blink_count` | int |
| `blink_rate` | float blinks/min |
| `blink_in_progress` | bool |
| `is_calibrating` | bool |
| `ear_threshold` | float |
| `face_detected` | bool |

### Output (post-session analysis)
| Metric | Type |
|--------|------|
| `total_blinks` | int |
| `session_duration_min` | float |
| `blink_rate` | float bpm |
| `short_blinks_count` | int |
| `long_blinks_count` | int |
| `abnormal_blink_count` | int |
| `duration_std` | float |
| `blink_log` | list of {blink_id, timestamp, duration} |
| `rate_status` | "low" / "normal" / "high" |
| `abnormality_flags` | list of strings |

### Algorithm Flow
1. Calibrate: collect EAR values for 2 seconds → median × 0.70 = threshold
2. Per frame: compute EAR from 6-point eye landmarks (both eyes averaged)
3. Apply smoothing window (3 frames)
4. If EAR < threshold → blink started (record start time)
5. When EAR rises above threshold → blink ended, measure duration
6. If duration within [0.03, 1.2] → valid blink, log it
7. Compute live blink rate = (count / elapsed) × 60

### Webcam / Desktop Code to Refactor
- `cv2.VideoCapture` → caller provides frames
- `cv2.imshow` / `cv2.waitKey` → remove
- `csv` / `pandas` export → move to report service
- `matplotlib` → move chart data to API response, render in React

### Reusable Functions
- `euclidean(a, b)` — pure
- `eye_aspect_ratio(eye_points)` — pure
- `landmark_list_to_points(landmarks, indices, w, h)` — pure

### Expected Web API Output (per frame)
```json
{
  "face_detected": true,
  "is_calibrating": false,
  "ear": 0.287,
  "ear_threshold": 0.210,
  "blink_count": 12,
  "blink_rate": 14.3,
  "blink_in_progress": false,
  "last_blink_duration": 0.12
}
```

---

## 3. facial_asymmetry.py

### Purpose
Detects facial asymmetry in real-time by comparing:
- Eye Aspect Ratio (left vs right)
- Mouth corner height asymmetry
- Brow height asymmetry
Produces a weighted composite asymmetry score with calibration and event detection.
Also detects rapid microexpression-like changes.

### Dependencies
- `cv2` (OpenCV)
- `mediapipe` (mp.solutions.face_mesh, refine_landmarks=True)
- `numpy`
- `collections.deque, namedtuple`
- `time`, `csv`

### Landmark Indices
```
LEFT_EYE_IDX  = [33, 160, 158, 133, 153, 144]
RIGHT_EYE_IDX = [362, 385, 387, 263, 373, 380]
MOUTH_LEFT=61, MOUTH_RIGHT=291
BROW_LEFT=70, BROW_RIGHT=300
OUTER_LEFT_EYE=33, OUTER_RIGHT_EYE=263
```

### Constants / Thresholds
| Name | Value | Meaning |
|------|-------|---------|
| CALIBRATE_SECONDS | 3.0 | Neutral-face calibration window |
| SMOOTH_WINDOW | 5 | Smoothing deque for all metrics |
| ASYM_THRESHOLD | 0.15 | Composite score above = asymmetry |
| CONSEC_FRAMES_TO_ALERT | 6 | Frames above threshold to trigger event |
| CONSEC_FRAMES_TO_CLEAR | 6 | Frames below threshold to clear event |
| MICRO_THRESHOLD | 0.30 | Relative change to flag microexpression |
| MICRO_COOLDOWN_FRAMES | 12 | Min frames between micro detections |
| W_EYE=0.6, W_MOUTH=0.25, W_BROW=0.15 | — | Composite score weights |

### Input
- Live webcam frame (BGR numpy array)

### Output / Metrics (per frame)
| Metric | Type |
|--------|------|
| `asym_score` | float — weighted composite (main metric) |
| `eye_asym` | float — relative eye EAR asymmetry |
| `mouth_asym` | float — mouth corner vertical asymmetry |
| `brow_asym` | float — brow height asymmetry (normalized by inter-ocular distance) |
| `is_calibrating` | bool |
| `asym_event_active` | bool — sustained asymmetry in progress |
| `face_detected` | bool |

### Output (per session / events)
| Metric | Type |
|--------|------|
| `asym_events` | list of {start, end, duration_s, max_score} |
| `micro_events` | list of {time, type, value} |
| `avg_asym_score` | float |

### Algorithm Flow
1. Calibrate 3 seconds: collect EAR left/right, mouth_asym, brow_asym
2. Per frame: compute all four raw metrics
3. Smooth each with 5-frame deque
4. Compute weighted composite: `0.6*eye_rel + 0.25*mouth + 0.15*brow`
5. Event logic: 6 consecutive frames above 0.15 → event starts; 6 below → event ends
6. Microexpression: >30% relative change in mouth or brow → flag (with cooldown)

### Webcam / Desktop Code to Refactor
- `cv2.VideoCapture` → caller provides frames
- `cv2.imshow` / `cv2.waitKey` → remove
- CSV export → move to report service
- `while True:` + `try/finally` cleanup → class-based service

### Reusable Functions
- `euclid(a, b)` — pure
- `lm_to_point(lm, idx, w, h)` — pure
- `compute_ear_from_indices(lm, indices, w, h)` — pure
- `micro_allowed(cur, prev, threshold)` — pure

### Expected Web API Output (per frame)
```json
{
  "face_detected": true,
  "is_calibrating": false,
  "asym_score": 0.112,
  "eye_asym": 0.089,
  "mouth_asym": 0.043,
  "brow_asym": 0.021,
  "asym_event_active": false,
  "asym_events_count": 1
}
```

---

## 4. ptosis_detector.py

### Purpose
Detects eyelid drooping (ptosis) by computing an Eye Opening Ratio (EOR)
for each eye using MediaPipe Face Mesh landmarks.
Calibrates to the user's baseline, then flags when either eye drops below 70% of baseline.

### Dependencies
- `cv2` (OpenCV)
- `mediapipe` (mp.solutions.face_mesh, refine_landmarks=True)
- `numpy`
- `time`

### Landmark Indices
```
LEFT_EYE  = [33, 160, 158, 133, 153, 144]
RIGHT_EYE = [362, 385, 387, 263, 373, 380]
```
Note: uses indices [1],[2] for vertical, [0],[3] for horizontal (different from EAR formula)

### Constants / Thresholds
| Name | Value | Meaning |
|------|-------|---------|
| Calibration window | 5 seconds | Baseline EOR collection |
| Drop threshold | 0.70 | `current < baseline * 0.70` → ptosis |
| MONITOR_DURATION | 30 s | Desktop-only hard limit |

### Eye Opening Ratio Formula
```
EOR = vertical / horizontal
  vertical  = dist(landmark[1], landmark[2])  → coords[1] - coords[2]
  horizontal= dist(landmark[0], landmark[3])  → coords[0] - coords[3]
```

### Input
- Live webcam frame (BGR numpy array)

### Output / Metrics (per frame)
| Metric | Type |
|--------|------|
| `left_ratio` | float — left eye EOR |
| `right_ratio` | float — right eye EOR |
| `base_left` | float — calibrated baseline left |
| `base_right` | float — calibrated baseline right |
| `left_drop` | bool — left eye dropped > 30% below baseline |
| `right_drop` | bool — right eye dropped > 30% below baseline |
| `ptosis_detected` | bool — either eye drooping |
| `is_calibrating` | bool |
| `face_detected` | bool |

### Algorithm Flow
1. First 5 seconds: collect left_ratio and right_ratio → baseline medians
2. Post-calibration per frame:
   - Compute current EOR for each eye
   - Compare to baseline with 0.70 threshold
   - Flag left_drop / right_drop / ptosis_detected

### Webcam / Desktop Code to Refactor
- `cv2.VideoCapture` → caller provides frames
- `cv2.imshow` / `cv2.waitKey` → remove
- `MONITOR_DURATION` hard stop → remove (web session controls duration)
- Module-level global `face_mesh` instance → move into service class

### Reusable Functions
- `eye_opening_ratio(landmarks, eye_indices, w, h)` — pure function, keep as-is

### Expected Web API Output (per frame)
```json
{
  "face_detected": true,
  "is_calibrating": false,
  "left_ratio": 0.28,
  "right_ratio": 0.19,
  "base_left": 0.31,
  "base_right": 0.30,
  "left_drop": false,
  "right_drop": true,
  "ptosis_detected": true
}
```
