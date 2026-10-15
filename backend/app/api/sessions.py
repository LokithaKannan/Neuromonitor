"""Session management endpoints."""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.db.base import get_db
from app.models.user import User
from app.models.session import (
    MonitoringSession, TremorResult, BlinkResult,
    AsymmetryResult, PtosisResult, SessionStatus,
)
from app.schemas.session import SessionCreate, SessionResponse, SessionWithResults

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    payload: SessionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = MonitoringSession(
        user_id=current_user.id,
        assessment_type=payload.assessment_type,
        notes=payload.notes,
        status=SessionStatus.active,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


@router.get("", response_model=list[SessionResponse])
async def list_sessions(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(MonitoringSession)
        .where(MonitoringSession.user_id == current_user.id)
        .order_by(MonitoringSession.started_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


@router.get("/{session_id}", response_model=SessionWithResults)
async def get_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(MonitoringSession)
        .where(MonitoringSession.id == session_id, MonitoringSession.user_id == current_user.id)
        .options(
            selectinload(MonitoringSession.tremor_results),
            selectinload(MonitoringSession.blink_results),
            selectinload(MonitoringSession.asymmetry_results),
            selectinload(MonitoringSession.ptosis_results),
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return session


@router.patch("/{session_id}/complete", response_model=SessionResponse)
async def complete_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(MonitoringSession).where(
            MonitoringSession.id == session_id,
            MonitoringSession.user_id == current_user.id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    session.status = SessionStatus.completed
    session.ended_at = datetime.now(timezone.utc)
    if session.started_at:
        delta = session.ended_at - session.started_at
        session.duration_seconds = round(delta.total_seconds(), 2)
    await db.commit()
    await db.refresh(session)
    return session


@router.post("/{session_id}/results/tremor", status_code=status.HTTP_201_CREATED)
async def save_tremor_result(
    session_id: int,
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _verify_session_ownership(session_id, current_user.id, db)
    result = TremorResult(
        session_id=session_id,
        recorded_at=datetime.now(timezone.utc),
        max_frequency_hz=data.get("max_frequency"),
        mean_amplitude_px=data.get("mean_amplitude"),
        dominant_severity=data.get("dominant_severity"),
        frames_with_hand=data.get("frames_with_hand"),
        total_frames=data.get("total_frames"),
        time_series=data.get("time_series"),
    )
    db.add(result)
    await db.commit()
    return {"status": "saved"}


@router.post("/{session_id}/results/blink", status_code=status.HTTP_201_CREATED)
async def save_blink_result(
    session_id: int,
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _verify_session_ownership(session_id, current_user.id, db)
    result = BlinkResult(
        session_id=session_id,
        recorded_at=datetime.now(timezone.utc),
        total_blinks=data.get("total_blinks"),
        session_duration_min=data.get("session_duration_min"),
        blink_rate=data.get("blink_rate"),
        short_blinks_count=data.get("short_blinks_count"),
        long_blinks_count=data.get("long_blinks_count"),
        abnormal_blink_count=data.get("abnormal_blink_count"),
        duration_std=data.get("duration_std"),
        rate_status=data.get("rate_status"),
        abnormality_flags=data.get("abnormality_flags"),
        blink_log=data.get("blink_log"),
    )
    db.add(result)
    await db.commit()
    return {"status": "saved"}


@router.post("/{session_id}/results/asymmetry", status_code=status.HTTP_201_CREATED)
async def save_asymmetry_result(
    session_id: int,
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _verify_session_ownership(session_id, current_user.id, db)
    result = AsymmetryResult(
        session_id=session_id,
        recorded_at=datetime.now(timezone.utc),
        avg_asym_score=data.get("avg_asym_score"),
        asym_events_count=data.get("asym_events_count"),
        micro_events_count=data.get("micro_events_count"),
        asym_events=data.get("asym_events"),
        micro_events=data.get("micro_events"),
        threshold_used=data.get("threshold_used"),
    )
    db.add(result)
    await db.commit()
    return {"status": "saved"}


@router.post("/{session_id}/results/ptosis", status_code=status.HTTP_201_CREATED)
async def save_ptosis_result(
    session_id: int,
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _verify_session_ownership(session_id, current_user.id, db)
    result = PtosisResult(
        session_id=session_id,
        recorded_at=datetime.now(timezone.utc),
        ptosis_alerted=data.get("ptosis_alerted"),
        ptosis_detected_frames=data.get("ptosis_detected_frames"),
        total_monitored_frames=data.get("total_monitored_frames"),
        ptosis_fraction=data.get("ptosis_fraction"),
        mean_left_ratio=data.get("mean_left_ratio"),
        mean_right_ratio=data.get("mean_right_ratio"),
        base_left=data.get("base_left"),
        base_right=data.get("base_right"),
    )
    db.add(result)
    await db.commit()
    return {"status": "saved"}


async def _verify_session_ownership(session_id: int, user_id: int, db: AsyncSession):
    result = await db.execute(
        select(MonitoringSession).where(
            MonitoringSession.id == session_id,
            MonitoringSession.user_id == user_id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
