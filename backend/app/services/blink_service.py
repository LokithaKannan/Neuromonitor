"""
Blink Detection Service — MediaPipe Tasks API (mediapipe >= 1.0)
Preserves all original EAR algorithms.
"""

import os
import time
import numpy as np
from collections import deque
from typing import Optional

import cv2
import mediapipe as mp

_VisionRunningMode      = mp.tasks.vision.RunningMode
_FaceLandmarker         = mp.tasks.vision.FaceLandmarker
_FaceLandmarkerOptions  = mp.tasks.vision.FaceLandmarkerOptions
_BaseOptions            = mp.tasks.BaseOptions
_MpImage                = mp.Image
_ImageFormat            = mp.ImageFormat

_MODEL_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'models', 'face_landmarker.task')

# --- Original constants (unchanged) ---
CALIBRATION_SECONDS    = 2.0
SMOOTHING_WINDOW       = 3
EAR_THRESHOLD_FACTOR   = 0.70
MIN_BLINK_DURATION     = 0.03
MAX_BLINK_DURATION     = 1.2
FALLBACK_EAR_THRESHOLD = 0.21

LEFT_EYE_IDX  = [33, 160, 158, 133, 153, 144]
RIGHT_EYE_IDX = [362, 385, 387, 263, 373, 380]

NORMAL_BLINK_MIN = 0.08
NORMAL_BLINK_MAX = 0.60
NORMAL_RATE_MIN  = 10
NORMAL_RATE_MAX  = 20


def euclidean(a, b) -> float:
    return float(np.linalg.norm(np.array(a) - np.array(b)))


def eye_aspect_ratio(eye_points) -> float:
    p1, p2, p3, p4, p5, p6 = eye_points
    A = euclidean(p2, p6)
    B = euclidean(p3, p5)
    C = euclidean(p1, p4)
    return (A + B) / (2.0 * C) if C > 0 else 0.0


def landmark_list_to_points(landmarks, indices, img_w, img_h):
    return [
        (int(landmarks[idx].x * img_w), int(landmarks[idx].y * img_h))
        for idx in indices
    ]


class BlinkService:
    """
    Stateful blink detection service using the new MediaPipe Tasks API.
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
        self.ear_history: deque        = deque(maxlen=SMOOTHING_WINDOW)
        self.blink_log: list[dict]     = []
        self.blink_count: int          = 0
        self.blink_in_progress: bool   = False
        self.blink_start_time: Optional[float] = None

        self.calibrating: bool         = True
        self.calib_ears: list[float]   = []
        self.calib_start_time: float   = time.time()
        self.baseline_open_ear: Optional[float] = None
        self.ear_threshold: float      = FALLBACK_EAR_THRESHOLD

    def reset(self) -> None:
        self._reset_state()

    def process_frame(self, frame: np.ndarray) -> dict:
        img_h, img_w = frame.shape[:2]
        rgb      = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = _MpImage(image_format=_ImageFormat.SRGB, data=rgb)
        result   = self._landmarker.detect(mp_image)
        current_time = time.time()

        ear: Optional[float] = None
        face_detected = False

        # result.face_landmarks is list[list[NormalizedLandmark]]
        if result.face_landmarks:
            face_detected = True
            landmarks = result.face_landmarks[0]
            left_pts  = landmark_list_to_points(landmarks, LEFT_EYE_IDX,  img_w, img_h)
            right_pts = landmark_list_to_points(landmarks, RIGHT_EYE_IDX, img_w, img_h)
            ear = (eye_aspect_ratio(left_pts) + eye_aspect_ratio(right_pts)) / 2.0

        # --- Calibration phase ---
        if self.calibrating:
            if ear is not None:
                self.calib_ears.append(ear)
            if current_time - self.calib_start_time >= CALIBRATION_SECONDS:
                if len(self.calib_ears) >= 5:
                    self.baseline_open_ear = float(np.median(self.calib_ears))
                    self.ear_threshold = self.baseline_open_ear * EAR_THRESHOLD_FACTOR
                else:
                    self.baseline_open_ear = None
                    self.ear_threshold = FALLBACK_EAR_THRESHOLD
                self.calibrating = False

            return {
                "face_detected":      face_detected,
                "is_calibrating":     True,
                "ear":                round(ear, 4) if ear is not None else None,
                "ear_threshold":      round(self.ear_threshold, 4),
                "blink_count":        self.blink_count,
                "blink_rate":         0.0,
                "blink_in_progress":  False,
                "last_blink_duration": None,
                "timestamp":          current_time,
            }

        # --- Detection phase ---
        ear_smooth: Optional[float] = None
        last_blink_duration: Optional[float] = None

        if ear is not None:
            self.ear_history.append(ear)
            ear_smooth = float(np.mean(self.ear_history))

        if ear_smooth is not None and ear_smooth < self.ear_threshold:
            if not self.blink_in_progress:
                self.blink_in_progress = True
                self.blink_start_time = current_time
        else:
            if self.blink_in_progress:
                blink_end_time = current_time
                duration = blink_end_time - (self.blink_start_time or blink_end_time)
                if MIN_BLINK_DURATION <= duration <= MAX_BLINK_DURATION:
                    self.blink_count += 1
                    last_blink_duration = duration
                    self.blink_log.append({
                        "blink_id":  self.blink_count,
                        "timestamp": blink_end_time - self.calib_start_time,
                        "duration":  round(duration, 4),
                    })
                self.blink_in_progress = False
                self.blink_start_time = None

        elapsed    = current_time - self.calib_start_time
        blink_rate = (self.blink_count / elapsed) * 60.0 if elapsed > 0 else 0.0

        return {
            "face_detected":      face_detected,
            "is_calibrating":     False,
            "ear":                round(ear_smooth, 4) if ear_smooth is not None else None,
            "ear_threshold":      round(self.ear_threshold, 4),
            "blink_count":        self.blink_count,
            "blink_rate":         round(blink_rate, 2),
            "blink_in_progress":  self.blink_in_progress,
            "last_blink_duration": round(last_blink_duration, 4) if last_blink_duration else None,
            "timestamp":          current_time,
        }

    def get_summary(self) -> dict:
        if not self.blink_log:
            return {
                "total_blinks":         0,
                "session_duration_min": 0.0,
                "blink_rate":           0.0,
                "short_blinks_count":   0,
                "long_blinks_count":    0,
                "abnormal_blink_count": 0,
                "duration_std":         0.0,
                "rate_status":          "unknown",
                "abnormality_flags":    [],
                "blink_log":            [],
            }

        durations    = [b["duration"]  for b in self.blink_log]
        timestamps   = [b["timestamp"] for b in self.blink_log]
        total_blinks = len(self.blink_log)
        session_time = (timestamps[-1] - timestamps[0]) / 60.0 if len(timestamps) > 1 else 0.0
        blink_rate   = total_blinks / session_time if session_time > 0 else 0.0

        short_blinks   = [d for d in durations if d < NORMAL_BLINK_MIN]
        long_blinks    = [d for d in durations if d > NORMAL_BLINK_MAX]
        abnormal_count = len(short_blinks) + len(long_blinks)
        duration_std   = float(np.std(durations)) if len(durations) > 1 else 0.0

        if blink_rate < NORMAL_RATE_MIN:
            rate_status = "low"
        elif blink_rate > NORMAL_RATE_MAX:
            rate_status = "high"
        else:
            rate_status = "normal"

        flags = []
        if blink_rate < NORMAL_RATE_MIN:
            flags.append("Low blink rate — possible Parkinsonism or fatigue")
        elif blink_rate > NORMAL_RATE_MAX:
            flags.append("High blink rate — possible ocular irritation or stress")
        if short_blinks:
            flags.append("Very short blinks detected — possible neuromuscular weakness")
        if long_blinks:
            flags.append("Prolonged blinks detected — possible fatigue or neurological issue")
        if duration_std > 0.15:
            flags.append("High blink duration variability — possible impairment")

        return {
            "total_blinks":         total_blinks,
            "session_duration_min": round(session_time, 3),
            "blink_rate":           round(blink_rate, 2),
            "short_blinks_count":   len(short_blinks),
            "long_blinks_count":    len(long_blinks),
            "abnormal_blink_count": abnormal_count,
            "duration_std":         round(duration_std, 4),
            "rate_status":          rate_status,
            "abnormality_flags":    flags,
            "blink_log":            self.blink_log,
        }

    def close(self) -> None:
        self._landmarker.close()
