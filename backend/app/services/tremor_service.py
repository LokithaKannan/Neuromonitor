"""
Tremor Detection Service — MediaPipe Tasks API (mediapipe >= 1.0)
Preserves all original FFT/amplitude algorithms.
"""

import os
import time
import numpy as np
from collections import deque
from typing import Optional

import cv2
import mediapipe as mp

_VisionRunningMode    = mp.tasks.vision.RunningMode
_HandLandmarker       = mp.tasks.vision.HandLandmarker
_HandLandmarkerOptions = mp.tasks.vision.HandLandmarkerOptions
_BaseOptions          = mp.tasks.BaseOptions
_MpImage              = mp.Image
_ImageFormat          = mp.ImageFormat

# Path to downloaded .task model
_MODEL_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'models', 'hand_landmarker.task')


def classify_tremor_severity(amplitude: float, frequency: float) -> str:
    """Original classification logic — unchanged."""
    if frequency < 1:
        return "No tremor"
    if frequency < 4:
        if amplitude < 2:
            return "Low-freq mild tremor"
        elif amplitude < 5:
            return "Low-freq moderate tremor"
        else:
            return "Low-freq severe tremor"
    elif 4 <= frequency <= 12:
        if amplitude < 2:
            return "Mild physiological tremor"
        elif amplitude < 5:
            return "Moderate physiological tremor"
        else:
            return "Severe physiological tremor"
    else:
        if amplitude < 2:
            return "High-freq mild tremor"
        elif amplitude < 5:
            return "High-freq moderate tremor"
        else:
            return "High-freq severe tremor"


def calculate_movement_amplitude(positions: deque) -> float:
    """Original amplitude calculation — unchanged."""
    if len(positions) < 2:
        return 0.0
    distances = []
    for i in range(1, len(positions)):
        x1, y1, _ = positions[i - 1]
        x2, y2, _ = positions[i]
        dist = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
        distances.append(dist)
    return float(np.mean(distances))


def detect_tremor_frequency(positions: deque) -> float:
    """Original FFT-based frequency detection — unchanged."""
    if len(positions) < 30:
        return 0.0
    timestamps = np.array([t for _, _, t in positions])
    xs = np.array([x for x, _, _ in positions])
    ys = np.array([y for _, y, _ in positions])
    xs = xs - np.mean(xs)
    ys = ys - np.mean(ys)
    time_uniform = np.linspace(timestamps[0], timestamps[-1], len(timestamps))
    x_interp = np.interp(time_uniform, timestamps, xs)
    y_interp = np.interp(time_uniform, timestamps, ys)
    signal = x_interp + y_interp
    fft = np.fft.fft(signal)
    freqs = np.fft.fftfreq(len(signal), d=(time_uniform[1] - time_uniform[0]))
    power = np.abs(fft) ** 2
    idx = (freqs > 0) & (freqs < 20)
    if not np.any(idx):
        return 0.0
    peak_freq = freqs[idx][np.argmax(power[idx])]
    return float(abs(peak_freq))


class TremorService:
    """
    Stateful tremor detection service using the new MediaPipe Tasks API.
    One instance per monitoring session.
    """

    POSITIONS_MAXLEN = 150

    def __init__(self):
        model_path = os.path.abspath(_MODEL_PATH)
        opts = _HandLandmarkerOptions(
            base_options=_BaseOptions(model_asset_path=model_path),
            running_mode=_VisionRunningMode.IMAGE,
            num_hands=1,
            min_hand_detection_confidence=0.6,
            min_hand_presence_confidence=0.6,
            min_tracking_confidence=0.6,
        )
        self._landmarker = _HandLandmarker.create_from_options(opts)
        self.positions: deque = deque(maxlen=self.POSITIONS_MAXLEN)
        self._frame_results: list[dict] = []

    def reset(self) -> None:
        """Clear state for a new session."""
        self.positions.clear()
        self._frame_results.clear()

    def process_frame(self, frame: np.ndarray) -> dict:
        """Process a single BGR frame. Returns current tremor metrics."""
        h, w = frame.shape[:2]
        # Flip horizontally (matches original behaviour)
        frame_flipped = cv2.flip(frame, 1)
        # New API requires RGB uint8 numpy array
        rgb = cv2.cvtColor(frame_flipped, cv2.COLOR_BGR2RGB)
        mp_image = _MpImage(image_format=_ImageFormat.SRGB, data=rgb)
        result = self._landmarker.detect(mp_image)
        current_time = time.time()

        output = {
            "hand_detected": False,
            "frequency": 0.0,
            "amplitude": 0.0,
            "severity": "No tremor",
            "positions_count": len(self.positions),
            "timestamp": current_time,
            "is_calibrating": False,
        }

        # result.hand_landmarks is a list of lists (one per hand)
        if result.hand_landmarks:
            output["hand_detected"] = True
            for hand_lm_list in result.hand_landmarks:
                # Index finger tip = landmark 8
                lm = hand_lm_list[8]
                x = int(lm.x * w)
                y = int(lm.y * h)
                self.positions.append((x, y, current_time))

        if len(self.positions) >= 30:
            amp = calculate_movement_amplitude(self.positions)
            freq = detect_tremor_frequency(self.positions)
            severity = classify_tremor_severity(amp, freq)
            output.update({
                "frequency": round(freq, 3),
                "amplitude": round(amp, 3),
                "severity": severity,
                "positions_count": len(self.positions),
            })

        self._frame_results.append(output)
        return output

    def get_summary(self) -> dict:
        """Return end-of-session aggregate metrics."""
        if not self._frame_results:
            return {
                "max_frequency": 0.0,
                "mean_amplitude": 0.0,
                "dominant_severity": "No tremor",
                "frames_with_hand": 0,
                "total_frames": 0,
                "time_series": [],
            }

        frames_with_hand = [r for r in self._frame_results if r["hand_detected"]]
        frequencies = [r["frequency"] for r in frames_with_hand if r["frequency"] > 0]
        amplitudes  = [r["amplitude"]  for r in frames_with_hand if r["amplitude"]  > 0]
        severities  = [r["severity"]   for r in frames_with_hand]
        dominant    = max(set(severities), key=severities.count) if severities else "No tremor"

        # Downsample time-series to max 300 points for storage
        step = max(1, len(self._frame_results) // 300)
        time_series = [
            {
                "timestamp": r["timestamp"],
                "frequency": r["frequency"],
                "amplitude": r["amplitude"],
                "severity":  r["severity"],
            }
            for r in self._frame_results[::step]
        ]

        return {
            "max_frequency":     round(max(frequencies), 3) if frequencies else 0.0,
            "mean_amplitude":    round(float(np.mean(amplitudes)), 3) if amplitudes else 0.0,
            "dominant_severity": dominant,
            "frames_with_hand":  len(frames_with_hand),
            "total_frames":      len(self._frame_results),
            "time_series":       time_series,
        }

    def close(self) -> None:
        """Release MediaPipe resources."""
        self._landmarker.close()
