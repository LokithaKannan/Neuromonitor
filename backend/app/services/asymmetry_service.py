"""
Facial Asymmetry Detection Service — MediaPipe Tasks API (mediapipe >= 1.0)
Preserves all original weighted-composite-score algorithms.
"""

import os
import time
import numpy as np
from collections import deque
from typing import Optional

import cv2
import mediapipe as mp

_VisionRunningMode     = mp.tasks.vision.RunningMode
_FaceLandmarker        = mp.tasks.vision.FaceLandmarker
_FaceLandmarkerOptions = mp.tasks.vision.FaceLandmarkerOptions
_BaseOptions           = mp.tasks.BaseOptions
_MpImage               = mp.Image
_ImageFormat           = mp.ImageFormat

_MODEL_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'models', 'face_landmarker.task')

# --- Original constants (unchanged) ---
CALIBRATE_SECONDS       = 3.0
SMOOTH_WINDOW           = 5
ASYM_THRESHOLD          = 0.15
CONSEC_FRAMES_TO_ALERT  = 6
CONSEC_FRAMES_TO_CLEAR  = 6
MICRO_THRESHOLD         = 0.30
MICRO_COOLDOWN_FRAMES   = 12

W_EYE   = 0.6
W_MOUTH = 0.25
W_BROW  = 0.15

LEFT_EYE_IDX  = [33, 160, 158, 133, 153, 144]
RIGHT_EYE_IDX = [362, 385, 387, 263, 373, 380]
MOUTH_LEFT              = 61
MOUTH_RIGHT             = 291
BROW_LEFT               = 70
BROW_RIGHT              = 300
OUTER_LEFT_EYE_CORNER   = 33
OUTER_RIGHT_EYE_CORNER  = 263


def euclid(a, b) -> float:
    return float(np.linalg.norm(np.array(a) - np.array(b)))


def lm_to_point(lm, idx, w, h):
    return (int(lm[idx].x * w), int(lm[idx].y * h))


def compute_ear_from_indices(lm, indices, w, h) -> float:
    p = [lm_to_point(lm, i, w, h) for i in indices]
    A = euclid(p[1], p[5])
    B = euclid(p[2], p[4])
    C = euclid(p[0], p[3])
    return (A + B) / (2.0 * C) if C > 1e-6 else 0.0


def micro_allowed(cur: float, prev: float, threshold: float) -> bool:
    if prev is None:
        return False
    denom = max(prev, 1e-6)
    return abs(cur - prev) / denom > threshold


class AsymmetryService:
    """
    Stateful facial asymmetry detection service using the new MediaPipe Tasks API.
    One instance per monitoring session.
    """

    def __init__(self):
        model_path = os.path.abspath(_MODEL_PATH)
        opts = _FaceLandmarkerOptions(
            base_options=_BaseOptions(model_asset_path=model_path),
            running_mode=_VisionRunningMode.IMAGE,
            num_faces=1,
            min_face_detection_confidence=0.5,
            min_face_presence_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self._landmarker = _FaceLandmarker.create_from_options(opts)
        self._reset_state()

    def _reset_state(self) -> None:
        self.eye_left_buf:    deque = deque(maxlen=SMOOTH_WINDOW)
        self.eye_right_buf:   deque = deque(maxlen=SMOOTH_WINDOW)
        self.mouth_asym_buf:  deque = deque(maxlen=SMOOTH_WINDOW)
        self.brow_asym_buf:   deque = deque(maxlen=SMOOTH_WINDOW)
        self.asym_score_buf:  deque = deque(maxlen=SMOOTH_WINDOW)

        self.calib_eye_left:   list[float] = []
        self.calib_eye_right:  list[float] = []
        self.calib_mouth_asym: list[float] = []
        self.calib_brow_asym:  list[float] = []
        self.start_time: float = time.time()

        self.consec_above: int = 0
        self.consec_below: int = 0
        self.asym_event_active: bool = False
        self.asym_event_start: Optional[float] = None
        self.asym_event_max: float = 0.0
        self.asym_events: list[dict] = []

        self.micro_events: list[dict] = []
        self.micro_cooldown: int = 0
        self.prev_mouth_asym: Optional[float] = None
        self.prev_brow_asym:  Optional[float] = None

    def reset(self) -> None:
        self._reset_state()

    def process_frame(self, frame: np.ndarray) -> dict:
        h, w = frame.shape[:2]
        rgb      = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = _MpImage(image_format=_ImageFormat.SRGB, data=rgb)
        res      = self._landmarker.detect(mp_image)
        t        = time.time()

        output = {
            "face_detected":      False,
            "is_calibrating":     (t - self.start_time) < CALIBRATE_SECONDS,
            "asym_score":         0.0,
            "eye_asym":           0.0,
            "mouth_asym":         0.0,
            "brow_asym":          0.0,
            "asym_event_active":  self.asym_event_active,
            "asym_events_count":  len(self.asym_events),
            "micro_events_count": len(self.micro_events),
            "timestamp":          t,
        }

        if not res.face_landmarks:
            return output

        output["face_detected"] = True
        lm = res.face_landmarks[0]   # list of NormalizedLandmark

        # --- Compute raw metrics (original logic) ---
        left_ear  = compute_ear_from_indices(lm, LEFT_EYE_IDX, w, h)
        right_ear = compute_ear_from_indices(lm, RIGHT_EYE_IDX, w, h)
        eye_asym  = abs(left_ear - right_ear) / max(left_ear, right_ear, 1e-6)

        ml = lm_to_point(lm, MOUTH_LEFT, w, h)
        mr = lm_to_point(lm, MOUTH_RIGHT, w, h)
        mouth_width    = euclid(ml, mr)
        mouth_vert_diff = abs(ml[1] - mr[1])
        mouth_asym     = mouth_vert_diff / max(mouth_width, 1e-6)

        bl = lm_to_point(lm, BROW_LEFT, w, h)
        br = lm_to_point(lm, BROW_RIGHT, w, h)
        inter_ocular = euclid(
            lm_to_point(lm, OUTER_LEFT_EYE_CORNER, w, h),
            lm_to_point(lm, OUTER_RIGHT_EYE_CORNER, w, h),
        )
        brow_asym = abs(bl[1] - br[1]) / max(inter_ocular, 1e-6)

        # --- Smooth ---
        self.eye_left_buf.append(left_ear)
        self.eye_right_buf.append(right_ear)
        self.mouth_asym_buf.append(mouth_asym)
        self.brow_asym_buf.append(brow_asym)

        s_left  = float(np.mean(self.eye_left_buf))
        s_right = float(np.mean(self.eye_right_buf))
        s_mouth = float(np.mean(self.mouth_asym_buf))
        s_brow  = float(np.mean(self.brow_asym_buf))

        asym_score = (
            W_EYE   * (abs(s_left - s_right) / max(s_left, s_right, 1e-6))
            + W_MOUTH * s_mouth
            + W_BROW  * s_brow
        )
        self.asym_score_buf.append(asym_score)

        # --- Calibration collection ---
        if (t - self.start_time) < CALIBRATE_SECONDS:
            self.calib_eye_left.append(left_ear)
            self.calib_eye_right.append(right_ear)
            self.calib_mouth_asym.append(mouth_asym)
            self.calib_brow_asym.append(brow_asym)
            output.update({
                "asym_score": round(asym_score, 4),
                "eye_asym":   round(eye_asym, 4),
                "mouth_asym": round(s_mouth, 4),
                "brow_asym":  round(s_brow, 4),
            })
            return output

        # --- Post-calibration event detection ---
        cur_asym = float(np.mean(self.asym_score_buf))

        if cur_asym > ASYM_THRESHOLD:
            self.consec_above += 1
            self.consec_below = 0
        else:
            self.consec_below += 1
            self.consec_above = 0

        if self.consec_above >= CONSEC_FRAMES_TO_ALERT and not self.asym_event_active:
            self.asym_event_active = True
            self.asym_event_start  = t
            self.asym_event_max    = cur_asym

        if self.asym_event_active:
            self.asym_event_max = max(self.asym_event_max, cur_asym)
            if self.consec_below >= CONSEC_FRAMES_TO_CLEAR:
                self.asym_events.append({
                    "start":      self.asym_event_start,
                    "end":        t,
                    "duration_s": round(t - self.asym_event_start, 3),
                    "max_score":  round(self.asym_event_max, 4),
                })
                self.asym_event_active = False
                self.asym_event_start  = None

        # --- Microexpression detection ---
        if self.prev_mouth_asym is not None and micro_allowed(mouth_asym, self.prev_mouth_asym, MICRO_THRESHOLD):
            if self.micro_cooldown == 0:
                self.micro_events.append({"time": t, "type": "mouth", "value": round(mouth_asym, 4)})
                self.micro_cooldown = MICRO_COOLDOWN_FRAMES

        if self.prev_brow_asym is not None and micro_allowed(brow_asym, self.prev_brow_asym, MICRO_THRESHOLD):
            if self.micro_cooldown == 0:
                self.micro_events.append({"time": t, "type": "brow", "value": round(brow_asym, 4)})
                self.micro_cooldown = MICRO_COOLDOWN_FRAMES

        self.prev_mouth_asym = s_mouth
        self.prev_brow_asym  = s_brow
        if self.micro_cooldown > 0:
            self.micro_cooldown -= 1

        output.update({
            "asym_score":         round(cur_asym, 4),
            "eye_asym":           round(eye_asym, 4),
            "mouth_asym":         round(s_mouth, 4),
            "brow_asym":          round(s_brow, 4),
            "asym_event_active":  self.asym_event_active,
            "asym_events_count":  len(self.asym_events),
            "micro_events_count": len(self.micro_events),
        })
        return output

    def get_summary(self) -> dict:
        if self.asym_event_active and self.asym_event_start:
            t = time.time()
            self.asym_events.append({
                "start":      self.asym_event_start,
                "end":        t,
                "duration_s": round(t - self.asym_event_start, 3),
                "max_score":  round(self.asym_event_max, 4),
            })
            self.asym_event_active = False

        avg_asym = float(np.mean(self.asym_score_buf)) if len(self.asym_score_buf) > 0 else 0.0

        return {
            "avg_asym_score":     round(avg_asym, 4),
            "asym_events":        self.asym_events,
            "asym_events_count":  len(self.asym_events),
            "micro_events":       self.micro_events,
            "micro_events_count": len(self.micro_events),
            "threshold_used":     ASYM_THRESHOLD,
        }

    def close(self) -> None:
        self._landmarker.close()
