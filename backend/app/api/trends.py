"""Longitudinal trends endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.deps import get_current_user
from app.db.base import get_db
from app.models.user import User
from app.models.session import (
    MonitoringSession, TremorResult, BlinkResult,
    AsymmetryResult, PtosisResult, SessionStatus,
)

router = APIRouter(prefix="/trends", tags=["trends"])


@router.get("")
async def get_trends(
    metric: str = Query("tremor_frequency", description="Which metric to return"),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return time-series data for the requested metric across completed sessions."""

    # Fetch user's completed sessions
    sessions_result = await db.execute(
        select(MonitoringSession)
        .where(
            MonitoringSession.user_id == current_user.id,
            MonitoringSession.status == SessionStatus.completed,
        )
        .order_by(MonitoringSession.started_at.asc())
        .limit(limit)
    )
    sessions = sessions_result.scalars().all()
    session_ids = [s.id for s in sessions]
    session_map = {s.id: s for s in sessions}

    data_points = []

    if metric == "tremor_frequency":
        rows = await db.execute(
            select(TremorResult).where(TremorResult.session_id.in_(session_ids))
        )
        for row in rows.scalars():
            s = session_map.get(row.session_id)
            data_points.append({
                "session_id": row.session_id,
                "date": s.started_at.isoformat() if s else None,
                "value": row.max_frequency_hz,
                "label": "Max Tremor Frequency (Hz)",
            })

    elif metric == "tremor_amplitude":
        rows = await db.execute(
            select(TremorResult).where(TremorResult.session_id.in_(session_ids))
        )
        for row in rows.scalars():
            s = session_map.get(row.session_id)
            data_points.append({
                "session_id": row.session_id,
                "date": s.started_at.isoformat() if s else None,
                "value": row.mean_amplitude_px,
                "label": "Mean Tremor Amplitude (px)",
            })

    elif metric == "blink_rate":
        rows = await db.execute(
            select(BlinkResult).where(BlinkResult.session_id.in_(session_ids))
        )
        for row in rows.scalars():
            s = session_map.get(row.session_id)
            data_points.append({
                "session_id": row.session_id,
                "date": s.started_at.isoformat() if s else None,
                "value": row.blink_rate,
                "label": "Blink Rate (blinks/min)",
            })

    elif metric == "asym_score":
        rows = await db.execute(
            select(AsymmetryResult).where(AsymmetryResult.session_id.in_(session_ids))
        )
        for row in rows.scalars():
            s = session_map.get(row.session_id)
            data_points.append({
                "session_id": row.session_id,
                "date": s.started_at.isoformat() if s else None,
                "value": row.avg_asym_score,
                "label": "Avg Asymmetry Score",
            })

    elif metric == "ptosis_fraction":
        rows = await db.execute(
            select(PtosisResult).where(PtosisResult.session_id.in_(session_ids))
        )
        for row in rows.scalars():
            s = session_map.get(row.session_id)
            data_points.append({
                "session_id": row.session_id,
                "date": s.started_at.isoformat() if s else None,
                "value": row.ptosis_fraction,
                "label": "Ptosis Detection Fraction",
            })

    # Sort by date
    data_points.sort(key=lambda x: x["date"] or "")

    return {
        "metric": metric,
        "data_points": data_points,
        "count": len(data_points),
    }
