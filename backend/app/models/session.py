"""Monitoring session and per-module result models."""

import enum
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, DateTime, Enum, Float, ForeignKey,
    Integer, String, Text, JSON
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, _is_sqlite


class AssessmentType(str, enum.Enum):
    complete  = "complete"
    tremor    = "tremor"
    blink     = "blink"
    asymmetry = "asymmetry"
    ptosis    = "ptosis"


class SessionStatus(str, enum.Enum):
    active    = "active"
    completed = "completed"
    aborted   = "aborted"


# Use plain String for SQLite (no native enum type); use Enum for PostgreSQL
def _enum_col(enum_cls, name, **kwargs):
    if _is_sqlite:
        return mapped_column(String(50), **kwargs)
    return mapped_column(
        Enum(enum_cls, name=name, create_constraint=True),
        **kwargs,
    )


class MonitoringSession(Base):
    __tablename__ = "monitoring_sessions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    assessment_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default=SessionStatus.active, nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    tremor_results: Mapped[list["TremorResult"]] = relationship(back_populates="session", cascade="all, delete-orphan")
    blink_results: Mapped[list["BlinkResult"]] = relationship(back_populates="session", cascade="all, delete-orphan")
    asymmetry_results: Mapped[list["AsymmetryResult"]] = relationship(back_populates="session", cascade="all, delete-orphan")
    ptosis_results: Mapped[list["PtosisResult"]] = relationship(back_populates="session", cascade="all, delete-orphan")
    report: Mapped["Report | None"] = relationship(back_populates="session", cascade="all, delete-orphan")


class TremorResult(Base):
    __tablename__ = "tremor_results"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("monitoring_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # Summary metrics (stored once per session at completion)
    max_frequency_hz: Mapped[float | None] = mapped_column(Float, nullable=True)
    mean_amplitude_px: Mapped[float | None] = mapped_column(Float, nullable=True)
    dominant_severity: Mapped[str | None] = mapped_column(String(100), nullable=True)
    frames_with_hand: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_frames: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Raw time-series data (list of {timestamp, frequency, amplitude, severity})
    time_series: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    session: Mapped["MonitoringSession"] = relationship(back_populates="tremor_results")


class BlinkResult(Base):
    __tablename__ = "blink_results"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("monitoring_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    total_blinks: Mapped[int | None] = mapped_column(Integer, nullable=True)
    session_duration_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    blink_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    short_blinks_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    long_blinks_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    abnormal_blink_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_std: Mapped[float | None] = mapped_column(Float, nullable=True)
    rate_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    abnormality_flags: Mapped[list | None] = mapped_column(JSON, nullable=True)
    blink_log: Mapped[list | None] = mapped_column(JSON, nullable=True)

    session: Mapped["MonitoringSession"] = relationship(back_populates="blink_results")


class AsymmetryResult(Base):
    __tablename__ = "asymmetry_results"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("monitoring_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    avg_asym_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    asym_events_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    micro_events_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    asym_events: Mapped[list | None] = mapped_column(JSON, nullable=True)
    micro_events: Mapped[list | None] = mapped_column(JSON, nullable=True)
    threshold_used: Mapped[float | None] = mapped_column(Float, nullable=True)

    session: Mapped["MonitoringSession"] = relationship(back_populates="asymmetry_results")


class PtosisResult(Base):
    __tablename__ = "ptosis_results"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("monitoring_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ptosis_alerted: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    ptosis_detected_frames: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_monitored_frames: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ptosis_fraction: Mapped[float | None] = mapped_column(Float, nullable=True)
    mean_left_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    mean_right_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    base_left: Mapped[float | None] = mapped_column(Float, nullable=True)
    base_right: Mapped[float | None] = mapped_column(Float, nullable=True)

    session: Mapped["MonitoringSession"] = relationship(back_populates="ptosis_results")


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("monitoring_sessions.id", ondelete="CASCADE"), nullable=False, unique=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    report_format: Mapped[str] = mapped_column(String(10), default="pdf")

    session: Mapped["MonitoringSession"] = relationship(back_populates="report")
