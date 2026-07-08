"""
Pydantic schemas untuk request dan response FastAPI.
Semua response menggunakan format Opsi B (envelope + metadata).
"""
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


# ─── Envelope Response ─────────────────────────────────────────────────────────

class Meta(BaseModel):
    processing_time_ms: float | None = None
    pipeline_stages: list[str] = []
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class APIResponse(BaseModel):
    """Wrapper standar untuk semua response sukses."""
    success: bool = True
    data: Any
    meta: Meta = Field(default_factory=Meta)


class APIError(BaseModel):
    """Wrapper standar untuk semua response error."""
    success: bool = False
    error: str
    detail: str | None = None
    meta: Meta = Field(default_factory=Meta)


# ─── Request Schema ────────────────────────────────────────────────────────────

class PredictRequest(BaseModel):
    """
    Input dari model LogBERT + DeepSVDD.
    Field ini harus identik dengan output fungsi predict().
    """
    anomaly_score: float = Field(..., ge=0.0, le=1.0)
    is_anomaly: bool
    log_keys: list[str] = Field(default_factory=list)
    log_sequence: list[str] = Field(
        ...,
        min_length=1,
        description="Raw log lines dalam satu time window"
    )
    window_id: str = Field(..., min_length=1)
    timestamp: str = Field(..., description="ISO 8601 timestamp dari model")

    @field_validator("log_sequence")
    @classmethod
    def log_sequence_not_empty(cls, v: list[str]) -> list[str]:
        if not any(line.strip() for line in v):
            raise ValueError("log_sequence tidak boleh berisi string kosong semua")
        return v


# ─── Response Schemas ──────────────────────────────────────────────────────────

class RetrievedDocSchema(BaseModel):
    title: str
    category: str
    severity: str
    cosine_similarity: float
    original_rank: int
    rerank_score: float
    final_rank: int


class PredictData(BaseModel):
    """Data payload untuk response POST /predict."""
    alert_id: UUID
    window_id: str
    anomaly_score: float
    is_anomaly: bool
    skipped: bool = False          # True jika is_anomaly=False, pipeline tidak dijalankan
    alert_title: str | None = None
    alert_summary: str | None = None
    alert_context: str | None = None
    alert_recommendation: str | None = None
    severity: str | None = None
    telegram_status: str | None = None
    top_documents: list[RetrievedDocSchema] = []
    created_at: datetime


class AlertListItem(BaseModel):
    """Satu item dalam list GET /alerts."""
    id: UUID
    window_id: str
    anomaly_score: float
    is_anomaly: bool
    alert_title: str | None
    severity: str | None
    telegram_status: str
    created_at: datetime


class AlertDetail(BaseModel):
    """Detail lengkap untuk GET /alerts/{id}."""
    id: UUID
    window_id: str
    anomaly_score: float
    is_anomaly: bool
    log_keys: list[str] | None
    model_timestamp: str | None
    retrieved_docs: dict | None
    alert_title: str | None
    alert_summary: str | None
    alert_context: str | None
    alert_recommendation: str | None
    telegram_status: str
    created_at: datetime


class AlertListData(BaseModel):
    items: list[AlertListItem]
    total: int
    page: int
    limit: int
    total_pages: int


class HealthData(BaseModel):
    status: str                    # "healthy" | "degraded"
    database: str                  # "connected" | "error"
    knowledge_base_docs: int
    api_version: str = "1.0.0"
