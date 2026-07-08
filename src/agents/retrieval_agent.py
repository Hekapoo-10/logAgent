"""
Retrieval Agent — Modul 1 dari pipeline RAG.

Alur kerja (Two-Stage Retrieval):
Stage 1 — sentence-transformers + pgvector (cosine similarity)
    → Cepat, approximate, ambil top-5 kandidat dari knowledge base

Stage 2 — Nemotron Rerank API (nvidia/llama-nemotron-rerank-vl-1b-v2:free)
    → Purpose-built reranking model, beri relevance_score tiap kandidat
    → Urutkan ulang berdasarkan skor ini, ambil top-3 final

Kedua skor (cosine_similarity dan rerank_score) disimpan untuk keperluan
evaluasi: seberapa sering urutan berubah setelah reranking?
"""
from dataclasses import dataclass

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import settings
from src.rag.embedder import embed_text

CANDIDATE_POOL_SIZE = 5   # Jumlah kandidat dari Stage 1 sebelum di-rerank


# ─── Data Classes ──────────────────────────────────────────────────────────────

@dataclass
class RetrievedDocument:
    """Satu dokumen hasil two-stage retrieval."""
    title: str
    content: str
    category: str
    severity: str
    source_file: str

    # Stage 1: dari pgvector cosine similarity
    cosine_similarity: float
    original_rank: int       # Urutan berdasarkan cosine similarity (1 = tertinggi)

    # Stage 2: dari Nemotron rerank API
    rerank_score: float      # Relevance score dari reranker (lebih tinggi = lebih relevan)
    final_rank: int          # Urutan final setelah reranking


@dataclass
class RetrievalResult:
    """Output lengkap dari Retrieval Agent."""
    documents: list[RetrievedDocument]        # Top-K final setelah reranking
    candidates_before_rerank: list[dict]      # Top-5 dari Stage 1 (untuk evaluasi)
    query_used: str
    rerank_performed: bool                    # False jika rerank API gagal (fallback ke cosine)
    is_context_valid: bool
    validation_note: str


# ─── Stage 1: Cosine Similarity Search ────────────────────────────────────────

def _build_query(log_keys: list[str], log_sequence: list[str]) -> str:
    parts = []
    if log_keys:
        parts.append(" ".join(log_keys))
    if log_sequence:
        parts.append(" ".join(log_sequence[:3]))
    return " ".join(parts).strip()


async def _cosine_search(query_vector: list[float], db: AsyncSession) -> list:
    vector_str = "[" + ",".join(str(x) for x in query_vector) + "]"
    rows = await db.execute(text(f"""
        SELECT
            doc_metadata->>'title'    AS title,
            content,
            doc_metadata->>'category' AS category,
            doc_metadata->>'severity' AS severity,
            doc_metadata->>'source'   AS source_file,
            1 - (embedding <=> '{vector_str}'::vector) AS similarity
        FROM documents
        ORDER BY embedding <=> '{vector_str}'::vector
        LIMIT {CANDIDATE_POOL_SIZE}
    """))
    return rows.fetchall()


# ─── Stage 2: Nemotron Rerank API ─────────────────────────────────────────────

async def _rerank(query: str, candidate_rows: list) -> list[dict] | None:
    """
    Kirim query + kandidat ke Nemotron Rerank API.

    Returns:
        List of {index, relevance_score} diurutkan dari yang paling relevan,
        atau None jika API gagal (fallback ke cosine).
    """
    documents = [{"text": row.content} for row in candidate_rows]

    payload = {
        "model": settings.openrouter_rerank_model,
        "query": query,
        "documents": documents,
        "top_n": settings.rag_top_k,
    }

    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/deepl-fp",
        "X-Title": "BGL Log Anomaly Monitor",
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                settings.openrouter_rerank_url,
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()
            return sorted(data["results"], key=lambda x: x["relevance_score"], reverse=True)
    except Exception:
        return None   # Caller akan fallback ke cosine similarity


# ─── Validasi Konteks ─────────────────────────────────────────────────────────

def _validate_context(
    documents: list[RetrievedDocument],
    anomaly_score: float,
    rerank_performed: bool,
) -> tuple[bool, str]:
    if not documents:
        return False, "Tidak ada dokumen relevan ditemukan di knowledge base."

    top_cosine = documents[0].cosine_similarity
    if top_cosine < settings.rag_similarity_threshold:
        return (
            False,
            f"Cosine similarity tertinggi ({top_cosine:.3f}) di bawah threshold "
            f"({settings.rag_similarity_threshold}). Konteks mungkin kurang akurat.",
        )

    method = "cosine+rerank" if rerank_performed else "cosine only (rerank fallback)"
    return True, (
        f"Konteks valid [{method}]. "
        f"Cosine: {top_cosine:.3f}, "
        f"Rerank score: {documents[0].rerank_score:.4f}."
    )


# ─── Main Entry Point ──────────────────────────────────────────────────────────

async def run(
    log_keys: list[str],
    log_sequence: list[str],
    anomaly_score: float,
    db: AsyncSession,
    use_rerank: bool = True,
) -> RetrievalResult:
    """
    Jalankan Retrieval Agent (two-stage retrieval).

    Args:
        log_keys:       Log template keys dari output model
        log_sequence:   Raw log dalam satu time window
        anomaly_score:  Skor anomali dari model (0-1)
        db:             SQLAlchemy async session
        use_rerank:     Jika False, lewati Nemotron rerank (pakai cosine top-k saja).
                        Berguna untuk evaluasi perbandingan dengan vs tanpa rerank.

    Returns:
        RetrievalResult dengan dokumen final + data perbandingan untuk evaluasi
    """
    # ── Stage 1: embed query + cosine search ───────────────────────────────
    query = _build_query(log_keys, log_sequence)
    query_vector = embed_text(query)
    candidate_rows = await _cosine_search(query_vector, db)

    if not candidate_rows:
        return RetrievalResult(
            documents=[],
            candidates_before_rerank=[],
            query_used=query,
            rerank_performed=False,
            is_context_valid=False,
            validation_note="Tabel documents kosong. Jalankan scripts/ingest_rag.py.",
        )

    # Simpan Stage 1 result untuk evaluasi
    candidates_before_rerank = [
        {
            "rank": i + 1,
            "title": r.title,
            "category": r.category,
            "severity": r.severity,
            "cosine_similarity": float(r.similarity),
        }
        for i, r in enumerate(candidate_rows)
    ]

    # ── Stage 2: Nemotron rerank (dilewati jika use_rerank=False) ──────────
    rerank_results = await _rerank(query, candidate_rows) if use_rerank else None
    rerank_performed = rerank_results is not None

    if rerank_performed:
        # Susun dokumen berdasarkan urutan reranker
        final_docs = []
        for final_rank, result in enumerate(rerank_results, 1):
            row = candidate_rows[result["index"]]
            original_rank = result["index"] + 1
            final_docs.append(RetrievedDocument(
                title=row.title or "Unknown",
                content=row.content,
                category=row.category or "",
                severity=row.severity or "",
                source_file=row.source_file or "",
                cosine_similarity=float(row.similarity),
                original_rank=original_rank,
                rerank_score=float(result["relevance_score"]),
                final_rank=final_rank,
            ))
    else:
        # Fallback: pakai urutan cosine similarity
        final_docs = [
            RetrievedDocument(
                title=r.title or "Unknown",
                content=r.content,
                category=r.category or "",
                severity=r.severity or "",
                source_file=r.source_file or "",
                cosine_similarity=float(r.similarity),
                original_rank=i + 1,
                rerank_score=float(r.similarity),  # gunakan cosine sebagai proxy
                final_rank=i + 1,
            )
            for i, r in enumerate(candidate_rows[:settings.rag_top_k])
        ]

    is_valid, note = _validate_context(final_docs, anomaly_score, rerank_performed)

    return RetrievalResult(
        documents=final_docs,
        candidates_before_rerank=candidates_before_rerank,
        query_used=query,
        rerank_performed=rerank_performed,
        is_context_valid=is_valid,
        validation_note=note,
    )
