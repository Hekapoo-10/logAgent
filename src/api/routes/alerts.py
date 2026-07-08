"""
GET /alerts        — List alert history dengan pagination + filter
GET /alerts/{id}   — Detail satu alert
GET /health        — Status sistem
"""
import math
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas import (
    APIError, APIResponse, AlertDetail, AlertListData, AlertListItem, HealthData, Meta,
)
from src.database.connection import get_db
from src.database.models import AlertHistory, Document

router = APIRouter(tags=["Alerts & Health"])


# ─── GET /health ───────────────────────────────────────────────────────────────

@router.get("/health", response_model=APIResponse)
async def health(db: AsyncSession = Depends(get_db)):
    """Cek status koneksi database dan jumlah dokumen knowledge base."""
    db_status = "connected"
    doc_count = 0

    try:
        result = await db.execute(select(func.count()).select_from(Document))
        doc_count = result.scalar() or 0
    except Exception:
        db_status = "error"

    overall = "healthy" if db_status == "connected" else "degraded"

    return APIResponse(
        data=HealthData(
            status=overall,
            database=db_status,
            knowledge_base_docs=doc_count,
        ),
        meta=Meta(),
    )


# ─── GET /alerts ───────────────────────────────────────────────────────────────

@router.get("/alerts", response_model=APIResponse)
async def list_alerts(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    min_score: float = Query(default=None, ge=0.0, le=1.0),
    telegram_status: str = Query(default=None, pattern="^(sent|failed|pending|skipped)$"),
    db: AsyncSession = Depends(get_db),
):
    """
    List alert history.

    Filter opsional:
    - **min_score**: hanya tampilkan anomali dengan score >= nilai ini
    - **telegram_status**: filter berdasarkan status pengiriman (sent/failed/pending/skipped)
    - **page** + **limit**: pagination
    """
    query = select(AlertHistory).order_by(AlertHistory.created_at.desc())

    if min_score is not None:
        query = query.where(AlertHistory.anomaly_score >= min_score)
    if telegram_status is not None:
        query = query.where(AlertHistory.telegram_status == telegram_status)

    # Hitung total untuk pagination
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Ambil data dengan offset
    offset = (page - 1) * limit
    paginated = query.offset(offset).limit(limit)
    result = await db.execute(paginated)
    records = result.scalars().all()

    items = [
        AlertListItem(
            id=r.id,
            window_id=r.window_id,
            anomaly_score=r.anomaly_score,
            is_anomaly=r.is_anomaly,
            alert_title=r.alert_title,
            severity=r.alert_recommendation and r.alert_title and "HIGH",  # dari DB
            telegram_status=r.telegram_status,
            created_at=r.created_at,
        )
        for r in records
    ]

    return APIResponse(
        data=AlertListData(
            items=items,
            total=total,
            page=page,
            limit=limit,
            total_pages=math.ceil(total / limit) if total > 0 else 0,
        ),
        meta=Meta(),
    )


# ─── GET /alerts/{id} ──────────────────────────────────────────────────────────

@router.get("/alerts/{alert_id}", response_model=APIResponse)
async def get_alert(
    alert_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Ambil detail lengkap satu alert termasuk dokumen yang diretrieval dan penjelasan LLM."""
    result = await db.execute(
        select(AlertHistory).where(AlertHistory.id == alert_id)
    )
    record = result.scalar_one_or_none()

    if record is None:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} tidak ditemukan.")

    return APIResponse(
        data=AlertDetail(
            id=record.id,
            window_id=record.window_id,
            anomaly_score=record.anomaly_score,
            is_anomaly=record.is_anomaly,
            log_keys=record.log_keys,
            model_timestamp=record.model_timestamp,
            retrieved_docs=record.retrieved_docs,
            alert_title=record.alert_title,
            alert_summary=record.alert_summary,
            alert_context=record.alert_context,
            alert_recommendation=record.alert_recommendation,
            telegram_status=record.telegram_status,
            created_at=record.created_at,
        ),
        meta=Meta(),
    )
