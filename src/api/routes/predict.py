"""
POST /predict — Endpoint utama yang menjalankan full pipeline.

Alur:
1. Validasi input (Pydantic otomatis)
2. Jika is_anomaly=False → simpan ke DB, return early (tidak jalankan RAG)
3. Jika is_anomaly=True  → retrieval_agent → document_agent → simpan → Telegram
4. Return response Opsi B dengan processing_time_ms
"""
import time
import uuid
from datetime import datetime, timezone

import logging
from fastapi import APIRouter, Depends, HTTPException

logger = logging.getLogger(__name__)
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas import APIResponse, Meta, PredictData, PredictRequest, RetrievedDocSchema
from src.database.connection import get_db
from src.database.models import AlertHistory
from src.agents import retrieval_agent, document_agent

router = APIRouter(prefix="/predict", tags=["Pipeline"])


async def _save_alert(
    db: AsyncSession,
    req: PredictRequest,
    retrieval_result=None,
    alert_doc=None,
    telegram_status: str = "pending",
) -> AlertHistory:
    """Simpan hasil pipeline ke tabel alert_history."""

    retrieved_docs_json = None
    if retrieval_result:
        retrieved_docs_json = {
            "candidates_before_rerank": retrieval_result.candidates_before_rerank,
            "final_documents": [
                {
                    "title": d.title,
                    "category": d.category,
                    "severity": d.severity,
                    "cosine_similarity": d.cosine_similarity,
                    "rerank_score": d.rerank_score,
                    "original_rank": d.original_rank,
                    "final_rank": d.final_rank,
                }
                for d in retrieval_result.documents
            ],
            "rerank_performed": retrieval_result.rerank_performed,
            "validation_note": retrieval_result.validation_note,
        }

    record = AlertHistory(
        id=uuid.uuid4(),
        window_id=req.window_id,
        anomaly_score=req.anomaly_score,
        is_anomaly=req.is_anomaly,
        log_keys=req.log_keys or [],
        model_timestamp=req.timestamp,
        retrieved_docs=retrieved_docs_json,
        alert_title=alert_doc.title if alert_doc else None,
        alert_summary=alert_doc.summary if alert_doc else None,
        alert_context=alert_doc.context if alert_doc else None,
        alert_recommendation=alert_doc.recommendation if alert_doc else None,
        telegram_status=telegram_status,
    )
    db.add(record)
    await db.flush()   # dapatkan ID tanpa commit dulu
    return record


@router.post("", response_model=APIResponse)
async def predict(
    req: PredictRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Jalankan full anomaly pipeline.

    - Jika **is_anomaly=False**: simpan ke DB dan berhenti (tidak ada RAG/LLM call).
    - Jika **is_anomaly=True**: jalankan Retrieval Agent → Document Agent → simpan → Telegram.
    """
    start_time = time.monotonic()
    stages_completed: list[str] = []

    # ── Early exit jika bukan anomali ─────────────────────────────────────
    if not req.is_anomaly:
        record = await _save_alert(db, req, telegram_status="skipped")
        elapsed = (time.monotonic() - start_time) * 1000

        return APIResponse(
            data=PredictData(
                alert_id=record.id,
                window_id=req.window_id,
                anomaly_score=req.anomaly_score,
                is_anomaly=False,
                skipped=True,
                created_at=record.created_at or datetime.now(timezone.utc),
            ),
            meta=Meta(
                processing_time_ms=round(elapsed, 2),
                pipeline_stages=["saved_non_anomaly"],
            ),
        )

    # ── Stage 1: Retrieval Agent ───────────────────────────────────────────
    try:
        retrieval_result = await retrieval_agent.run(
            log_keys=req.log_keys,
            log_sequence=req.log_sequence,
            anomaly_score=req.anomaly_score,
            db=db,
        )
        stages_completed.append("retrieval_agent")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Retrieval Agent error: {e}")

    # ── Stage 2: Document Agent ────────────────────────────────────────────
    try:
        alert_doc = await document_agent.run(
            anomaly_score=req.anomaly_score,
            log_keys=req.log_keys,
            log_sequence=req.log_sequence,
            retrieval_result=retrieval_result,
        )
        stages_completed.append("document_agent")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Document Agent error: {e}")

    # ── Stage 3: Telegram ──────────────────────────────────────────────────
    telegram_status = "pending"
    try:
        from src.bot.telegram import send_alert
        await send_alert(alert_doc, req)
        telegram_status = "sent"
        stages_completed.append("telegram")
    except ImportError:
        telegram_status = "pending"
    except Exception as e:
        telegram_status = "failed"
        logger.error(f"Telegram error: {e}")

    # ── Simpan ke database ─────────────────────────────────────────────────
    record = await _save_alert(
        db, req, retrieval_result, alert_doc, telegram_status
    )
    stages_completed.append("saved_to_db")

    elapsed = (time.monotonic() - start_time) * 1000

    # ── Susun response ─────────────────────────────────────────────────────
    top_docs = [
        RetrievedDocSchema(
            title=d.title,
            category=d.category,
            severity=d.severity,
            cosine_similarity=d.cosine_similarity,
            original_rank=d.original_rank,
            rerank_score=d.rerank_score,
            final_rank=d.final_rank,
        )
        for d in retrieval_result.documents
    ]

    return APIResponse(
        data=PredictData(
            alert_id=record.id,
            window_id=req.window_id,
            anomaly_score=req.anomaly_score,
            is_anomaly=True,
            skipped=False,
            alert_title=alert_doc.title,
            alert_summary=alert_doc.summary,
            alert_context=alert_doc.context,
            alert_recommendation=alert_doc.recommendation,
            severity=alert_doc.severity,
            telegram_status=telegram_status,
            top_documents=top_docs,
            created_at=record.created_at or datetime.now(timezone.utc),
        ),
        meta=Meta(
            processing_time_ms=round(elapsed, 2),
            pipeline_stages=stages_completed,
        ),
    )
