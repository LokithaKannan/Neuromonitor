"""Session and results schemas."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel

from app.models.session import AssessmentType, SessionStatus


class SessionCreate(BaseModel):
    assessment_type: AssessmentType
    notes: Optional[str] = None


class SessionResponse(BaseModel):
    id: int
    user_id: int
    assessment_type: str
    status: str
    started_at: datetime
    ended_at: Optional[datetime]
    duration_seconds: Optional[float]
    notes: Optional[str]

    model_config = {"from_attributes": True}


class TremorResultResponse(BaseModel):
    id: int
    session_id: int
    recorded_at: datetime
    max_frequency_hz: Optional[float]
    mean_amplitude_px: Optional[float]
    dominant_severity: Optional[str]
    frames_with_hand: Optional[int]
    total_frames: Optional[int]
    time_series: Optional[Any]

    model_config = {"from_attributes": True}


class BlinkResultResponse(BaseModel):
    id: int
    session_id: int
    recorded_at: datetime
    total_blinks: Optional[int]
    session_duration_min: Optional[float]
    blink_rate: Optional[float]
    short_blinks_count: Optional[int]
    long_blinks_count: Optional[int]
    abnormal_blink_count: Optional[int]
    duration_std: Optional[float]
    rate_status: Optional[str]
    abnormality_flags: Optional[list]
    blink_log: Optional[list]

    model_config = {"from_attributes": True}


class AsymmetryResultResponse(BaseModel):
    id: int
    session_id: int
    recorded_at: datetime
    avg_asym_score: Optional[float]
    asym_events_count: Optional[int]
    micro_events_count: Optional[int]
    asym_events: Optional[list]
    micro_events: Optional[list]
    threshold_used: Optional[float]

    model_config = {"from_attributes": True}


class PtosisResultResponse(BaseModel):
    id: int
    session_id: int
    recorded_at: datetime
    ptosis_alerted: Optional[bool]
    ptosis_detected_frames: Optional[int]
    total_monitored_frames: Optional[int]
    ptosis_fraction: Optional[float]
    mean_left_ratio: Optional[float]
    mean_right_ratio: Optional[float]
    base_left: Optional[float]
    base_right: Optional[float]

    model_config = {"from_attributes": True}


class SessionWithResults(SessionResponse):
    tremor_results: list[TremorResultResponse] = []
    blink_results: list[BlinkResultResponse] = []
    asymmetry_results: list[AsymmetryResultResponse] = []
    ptosis_results: list[PtosisResultResponse] = []


class ProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    current_password: Optional[str] = None
    new_password: Optional[str] = None
