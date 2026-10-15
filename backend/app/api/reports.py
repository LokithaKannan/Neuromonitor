"""Report generation endpoints (PDF)."""

import io
import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.db.base import get_db
from app.models.user import User
from app.models.session import MonitoringSession, Report

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("/{session_id}", status_code=status.HTTP_201_CREATED)
async def generate_report(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate and return a PDF report for a completed session."""
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

    pdf_bytes = _build_pdf(current_user, session)

    # Store report metadata
    existing = await db.execute(select(Report).where(Report.session_id == session_id))
    if not existing.scalar_one_or_none():
        report = Report(
            session_id=session_id,
            user_id=current_user.id,
            report_format="pdf",
        )
        db.add(report)
        await db.commit()

    headers = {
        "Content-Disposition": f'attachment; filename="nms_report_session_{session_id}.pdf"'
    }
    return StreamingResponse(io.BytesIO(pdf_bytes), media_type="application/pdf", headers=headers)


def _build_pdf(user: User, session: MonitoringSession) -> bytes:
    """Build PDF using ReportLab."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.lib import colors
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
        )
        from reportlab.lib.enums import TA_CENTER, TA_LEFT
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="PDF generation library not installed. Run: pip install reportlab",
        )

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm,
                             leftMargin=2*cm, rightMargin=2*cm)
    styles = getSampleStyleSheet()
    story = []

    # Title
    title_style = ParagraphStyle("Title", parent=styles["Title"],
                                  textColor=colors.HexColor("#4A1942"),
                                  fontSize=20, spaceAfter=6)
    story.append(Paragraph("Neurological Monitoring Report", title_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#C07340")))
    story.append(Spacer(1, 0.3*cm))

    # Metadata table
    body = styles["BodyText"]
    meta = [
        ["Patient Name", user.full_name],
        ["Email", user.email],
        ["Assessment Type", session.assessment_type],
        ["Status", session.status],
        ["Date", session.started_at.strftime("%Y-%m-%d %H:%M UTC") if session.started_at else "—"],
        ["Duration", f"{session.duration_seconds:.0f} seconds" if session.duration_seconds else "—"],
    ]
    t = Table(meta, colWidths=[5*cm, 12*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F5F0EC")),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#4A1942")),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, colors.HexColor("#FAF7F4")]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E8DDD5")),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.5*cm))

    h2 = ParagraphStyle("H2", parent=styles["Heading2"],
                         textColor=colors.HexColor("#4A1942"), spaceBefore=12)

    # Tremor results
    if session.tremor_results:
        story.append(Paragraph("Tremor Analysis", h2))
        for r in session.tremor_results:
            rows = [
                ["Max Frequency", f"{r.max_frequency_hz:.2f} Hz" if r.max_frequency_hz is not None else "—"],
                ["Mean Amplitude", f"{r.mean_amplitude_px:.2f} px" if r.mean_amplitude_px is not None else "—"],
                ["Dominant Severity", r.dominant_severity or "—"],
                ["Frames with Hand", str(r.frames_with_hand or "—")],
            ]
            _append_result_table(story, rows)

    # Blink results
    if session.blink_results:
        story.append(Paragraph("Blink Analysis", h2))
        for r in session.blink_results:
            rows = [
                ["Total Blinks", str(r.total_blinks or "—")],
                ["Blink Rate", f"{r.blink_rate:.1f} blinks/min" if r.blink_rate is not None else "—"],
                ["Rate Status", r.rate_status or "—"],
                ["Abnormal Blinks", str(r.abnormal_blink_count or "—")],
                ["Duration Std Dev", f"{r.duration_std:.4f} s" if r.duration_std is not None else "—"],
            ]
            _append_result_table(story, rows)
            if r.abnormality_flags:
                for flag in r.abnormality_flags:
                    story.append(Paragraph(f"• {flag}", body))

    # Asymmetry results
    if session.asymmetry_results:
        story.append(Paragraph("Facial Asymmetry Analysis", h2))
        for r in session.asymmetry_results:
            rows = [
                ["Avg Asymmetry Score", f"{r.avg_asym_score:.4f}" if r.avg_asym_score is not None else "—"],
                ["Sustained Asymmetry Events", str(r.asym_events_count or "—")],
                ["Microexpression Events", str(r.micro_events_count or "—")],
                ["Threshold", f"{r.threshold_used:.2f}" if r.threshold_used is not None else "—"],
            ]
            _append_result_table(story, rows)

    # Ptosis results
    if session.ptosis_results:
        story.append(Paragraph("Ptosis Analysis", h2))
        for r in session.ptosis_results:
            rows = [
                ["Ptosis Detected", "Yes" if r.ptosis_alerted else "No"],
                ["Mean Left EOR", f"{r.mean_left_ratio:.4f}" if r.mean_left_ratio is not None else "—"],
                ["Mean Right EOR", f"{r.mean_right_ratio:.4f}" if r.mean_right_ratio is not None else "—"],
                ["Baseline Left", f"{r.base_left:.4f}" if r.base_left is not None else "—"],
                ["Baseline Right", f"{r.base_right:.4f}" if r.base_right is not None else "—"],
                ["Ptosis Fraction", f"{r.ptosis_fraction:.1%}" if r.ptosis_fraction is not None else "—"],
            ]
            _append_result_table(story, rows)

    # Disclaimer
    story.append(Spacer(1, 1*cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#C8B8B0")))
    disclaimer = ParagraphStyle("Disclaimer", parent=styles["Italic"],
                                 fontSize=8, textColor=colors.HexColor("#666666"))
    story.append(Paragraph(
        "DISCLAIMER: This report is generated by the Neurological Monitoring System for screening and "
        "monitoring purposes only. It does not constitute a medical diagnosis and is not a substitute "
        "for professional medical evaluation by a qualified healthcare provider.",
        disclaimer,
    ))

    doc.build(story)
    return buffer.getvalue()


def _append_result_table(story, rows):
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.platypus import Table, TableStyle, Spacer

    t = Table(rows, colWidths=[6*cm, 11*cm])
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F5F0EC")),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, colors.HexColor("#FAF7F4")]),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#E8DDD5")),
        ("PADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.3*cm))
