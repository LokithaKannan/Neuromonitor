"""
Ptosis Detection Service — MediaPipe Tasks API (mediapipe >= 1.0)
Preserves all original Eye Opening Ratio algorithms.
"""

import os
import time
import numpy as np
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
LEFT_EYE             = [33, 160, 158, 133, 153, 144]
RIGHT_EYE            = [362, 385, 387, 263, 373, 380]
CALIBRATION_SECONDS  = 5.0
PTOSIS_DROP_THRESHOLD = 0.70


def eye_opening_ratio(landmarks, eye_indices: list, w: int, h: int) -> float:
    """Original EOR formula — unchanged."""
    coords   = [(int(landmarks[i].x * w), int(landmarks[i].y * h)) for i in eye_indices]
    vertical = float(np.linalg.norm(np.array(coords[1]) - np.array(coords[2])))
    horizontal = float(np.linalg.norm(np.array(coords[0]) - np.array(coords[3])))
    return vertical / horizontal if horizontal > 0 else 0.0


class PtosisService:
    """
    Stateful ptosis detection service using the new MediaPipe Tasks API.
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
        self.baseline_left:  list[float] = []
        self.baseline_right: list[float] = []
        self.start_time: float = time.time()
        self.ptosis_alerted: bool = False
        self._frame_results: list[dict] = []

    def reset(self) -> None:
        self._reset_state()

    def process_frame(self, frame: np.ndarray) -> dict:
        h, w     = frame.shape[:2]
        rgb      = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = _MpImage(image_format=_ImageFormat.SRGB, data=rgb)
        result   = self._landmarker.detect(mp_image)
        t        = time.time()
        is_calibrating = (t - self.start_time) < CALIBRATION_SECONDS

        output = {
            "face_detected":  False,
            "is_calibrating": is_calibrating,
            "left_ratio":     0.0,
            "right_ratio":    0.0,
            "base_left":      0.0,
            "base_right":     0.0,
            "left_drop":      False,
            "right_drop":     False,
            "ptosis_detected": False,
            "timestamp":      t,
        }

        if not result.face_landmarks:
            self._frame_results.append(output)
            return output

        output["face_detected"] = True
        landmarks = result.face_landmarks[0]   # list of NormalizedLandmark

        left_ratio  = eye_opening_ratio(landmarks, LEFT_EYE,  w, h)
        right_ratio = eye_opening_ratio(landmarks, RIGHT_EYE, w, h)

        output["left_ratio"]  = round(left_ratio, 4)
        output["right_ratio"] = round(right_ratio, 4)

        if is_calibrating:
            self.baseline_left.append(left_ratio)
            self.baseline_right.append(right_ratio)
        else:
            base_left  = float(np.median(self.baseline_left))  if self.baseline_left  else 0.3
            base_right = float(np.median(self.baseline_right)) if self.baseline_right else 0.3

            left_drop  = left_ratio  < base_left  * PTOSIS_DROP_THRESHOLD
            right_drop = right_ratio < base_right * PTOSIS_DROP_THRESHOLD

            output.update({
                "base_left":       round(base_left, 4),
                "base_right":      round(base_right, 4),
                "left_drop":       left_drop,
                "right_drop":      right_drop,
                "ptosis_detected": left_drop or right_drop,
            })

            if left_drop or right_drop:
                self.ptosis_alerted = True

        self._frame_results.append(output)
        return output

    def get_summary(self) -> dict:
        frames_with_face = [
            r for r in self._frame_results
            if r["face_detected"] and not r["is_calibrating"]
        ]

        if not frames_with_face:
            return {
                "ptosis_alerted":        self.ptosis_alerted,
                "ptosis_detected_frames": 0,
                "total_monitored_frames": 0,
                "ptosis_fraction":        0.0,
                "mean_left_ratio":        0.0,
                "mean_right_ratio":       0.0,
                "base_left":              0.0,
                "base_right":             0.0,
            }

        ptosis_frames = [r for r in frames_with_face if r["ptosis_detected"]]
        left_ratios   = [r["left_ratio"]  for r in frames_with_face]
        right_ratios  = [r["right_ratio"] for r in frames_with_face]
        base_left     = float(np.median(self.baseline_left))  if self.baseline_left  else 0.0
        base_right    = float(np.median(self.baseline_right)) if self.baseline_right else 0.0

        return {
            "ptosis_alerted":        self.ptosis_alerted,
            "ptosis_detected_frames": len(ptosis_frames),
            "total_monitored_frames": len(frames_with_face),
            "ptosis_fraction":        round(len(ptosis_frames) / max(len(frames_with_face), 1), 4),
            "mean_left_ratio":        round(float(np.mean(left_ratios)), 4),
            "mean_right_ratio":       round(float(np.mean(right_ratios)), 4),
            "base_left":              round(base_left, 4),
            "base_right":             round(base_right, 4),
        }

    def close(self) -> None:
        self._landmarker.close()
