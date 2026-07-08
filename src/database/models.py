import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Float, Boolean, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.database.connection import Base


class Document(Base):
    """
    Knowledge base untuk RAG.
    Setiap baris adalah satu chunk dokumen tentang pola anomali BGL log,
    beserta vector embedding-nya untuk similarity search.

    Embedding bertipe VECTOR(384) sesuai model all-MiniLM-L6-v2.
    HNSW index dibuat di scripts/init_db.py untuk mempercepat similarity search.
    """
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(384), nullable=False)

    # Metadata fleksibel: source, kategori anomali, severity, dsb
    doc_metadata: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<Document id={self.id} content={self.content[:60]!r}>"


class AlertHistory(Base):
    """
    Rekaman setiap anomali yang terdeteksi dan sudah melalui full pipeline.
    Disimpan untuk keperluan audit dan evaluasi performa sistem.

    Alur pengisian kolom:
    - window_id, anomaly_score, is_anomaly, log_keys → dari output model (predict())
    - retrieved_docs                                  → dari Retrieval Agent
    - alert_title/summary/context/recommendation     → dari Document Agent
    - telegram_status                                 → setelah Telegram Bot kirim alert
    """
    __tablename__ = "alert_history"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # --- Output dari model ---
    window_id: Mapped[str] = mapped_column(String(100), nullable=False)
    anomaly_score: Mapped[float] = mapped_column(Float, nullable=False)
    is_anomaly: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    log_keys: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    model_timestamp: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # --- Output dari Retrieval Agent ---
    # List of {content, score, metadata} dari similarity search
    retrieved_docs: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # --- Output dari Document Agent ---
    alert_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    alert_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    alert_context: Mapped[str | None] = mapped_column(Text, nullable=True)
    alert_recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)

    # --- Status pengiriman Telegram ---
    # Nilai: "sent" | "failed" | "pending"
    telegram_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"<AlertHistory id={self.id} window={self.window_id} "
            f"score={self.anomaly_score:.3f} telegram={self.telegram_status}>"
        )
