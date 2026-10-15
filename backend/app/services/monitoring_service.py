"""
Monitoring Service — orchestrates per-session instances of the four detection services.
"""

import base64
import time
from typing import Optional

import cv2
import numpy as np

from app.services.tremor_service import TremorService
from app.services.blink_service import BlinkService
from app.services.asymmetry_service import AsymmetryService
from app.services.ptosis_service import PtosisService


VALID_MODULES = {"tremor", "blink", "asymmetry", "ptosis"}


def decode_frame(b64_data: str) -> Optional[np.ndarray]:
    """Decode a base64 JPEG/PNG string to a BGR numpy array."""
    try:
        if "," in b64_data:
            b64_data = b64_data.split(",", 1)[1]
        img_bytes = base64.b64decode(b64_data)
        arr = np.frombuffer(img_bytes, dtype=np.uint8)
        frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        return frame
    except Exception:
        return None


class MonitoringSession:
    """
    Holds all detection service instances for a single user monitoring session.
    Created when a WebSocket monitoring session starts, destroyed when it ends.
    """

    def __init__(self, session_id: str, modules: list[str]):
        self.session_id = session_id
        self.modules = [m for m in modules if m in VALID_MODULES]
        self.started_at = time.time()
        self.ended_at: Optional[float] = None

        self._services: dict = {}
        if "tremor" in self.modules:
            self._services["tremor"] = TremorService()
        if "blink" in self.modules:
            self._services["blink"] = BlinkService()
        if "asymmetry" in self.modules:
            self._services["asymmetry"] = AsymmetryService()
        if "ptosis" in self.modules:
            self._services["ptosis"] = PtosisService()

    def process_frame(self, b64_frame: str, requested_modules: Optional[list[str]] = None) -> dict:
        """
        Decode frame and run all (or specified) active modules.
        Returns dict keyed by module name.
        """
        frame = decode_frame(b64_frame)
        if frame is None:
            return {"error": "Failed to decode frame"}

        target = requested_modules if requested_modules else self.modules
        results = {"timestamp": time.time(), "modules": {}}

        for module in target:
            if module not in self._services:
                continue
            try:
                results["modules"][module] = self._services[module].process_frame(frame)
            except Exception as exc:
                results["modules"][module] = {"error": str(exc)}

        return results

    def get_summary(self) -> dict:
        """Collect end-of-session summaries from all active services."""
        self.ended_at = time.time()
        summaries = {}
        for module, service in self._services.items():
            try:
                summaries[module] = service.get_summary()
            except Exception as exc:
                summaries[module] = {"error": str(exc)}
        return {
            "session_id": self.session_id,
            "modules": self.modules,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "duration_seconds": round(self.ended_at - self.started_at, 2),
            "summaries": summaries,
        }

    def close(self) -> None:
        """Release all MediaPipe resources."""
        for service in self._services.values():
            try:
                service.close()
            except Exception:
                pass


# In-memory registry of active sessions (keyed by session_id string)
_active_sessions: dict[str, MonitoringSession] = {}


def create_session(session_id: str, modules: list[str]) -> MonitoringSession:
    session = MonitoringSession(session_id, modules)
    _active_sessions[session_id] = session
    return session


def get_session(session_id: str) -> Optional[MonitoringSession]:
    return _active_sessions.get(session_id)


def end_session(session_id: str) -> Optional[dict]:
    session = _active_sessions.pop(session_id, None)
    if session is None:
        return None
    summary = session.get_summary()
    session.close()
    return summary
