"""
Document Agent — Modul 2 dari pipeline RAG.

Tanggung jawab:
1. Menerima RetrievalResult dari Retrieval Agent
2. Menyusun prompt berbasis konteks anomali + dokumen relevan
3. Mengirim ke LLM Nemotron via OpenRouter API
4. Mem-parsing respons LLM menjadi dokumen alert terstruktur
5. Mengembalikan AlertDocument yang siap dikirim ke Telegram dan disimpan ke DB
"""
import re
from dataclasses import dataclass

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from src.config.settings import settings
from src.agents.retrieval_agent import RetrievalResult


@dataclass
class AlertDocument:
    """Dokumen alert final yang dihasilkan Document Agent."""
    title: str
    summary: str
    context: str
    recommendation: str
    severity: str
    raw_llm_response: str


# ─── Prompt Templates ──────────────────────────────────────────────────────────

SYSTEM_PROMPT = """Kamu adalah sistem monitoring supercomputer BGL (BlueGene/L) yang bertugas
menganalisis anomali dan membuat laporan alert yang jelas, akurat, dan actionable.

Kamu akan menerima:
- Data anomali dari model deep learning (anomaly score, log keys, contoh log)
- Dokumen referensi dari knowledge base tentang pola anomali BGL

Tugasmu adalah menulis dokumen alert dalam format yang PERSIS seperti ini (gunakan label yang sama):

JUDUL: [judul singkat maksimal 10 kata yang menggambarkan anomali]

RINGKASAN: [1-2 kalimat ringkasan anomali yang terjadi, menggunakan bahasa Indonesia]

KONTEKS: [2-3 kalimat penjelasan teknis berdasarkan dokumen referensi, apa yang kemungkinan terjadi dan mengapa berbahaya]

REKOMENDASI: [2-3 poin tindakan spesifik yang perlu dilakukan, gunakan bullet point dengan tanda "-"]

SEVERITY: [pilih satu: CRITICAL / HIGH / MEDIUM / LOW]

Gunakan bahasa Indonesia. Jangan tambahkan teks apapun di luar format di atas."""

USER_PROMPT_TEMPLATE = """DATA ANOMALI:
- Anomaly Score: {anomaly_score} (threshold: {threshold})
- Log Keys Terdeteksi: {log_keys}
- Contoh Log dari Window:
{log_samples}

DOKUMEN REFERENSI RELEVAN:
{reference_docs}

Validasi Konteks: {validation_note}

Buatkan dokumen alert berdasarkan data dan referensi di atas."""


def _build_user_prompt(
    anomaly_score: float,
    log_keys: list[str],
    log_sequence: list[str],
    retrieval_result: RetrievalResult,
) -> str:
    """Susun prompt user dengan semua konteks yang diperlukan."""

    # Format log samples (maks 5 baris)
    log_samples = "\n".join(f"  • {log}" for log in log_sequence[:5])
    if len(log_sequence) > 5:
        log_samples += f"\n  ... ({len(log_sequence) - 5} log lainnya)"

    # Format dokumen referensi
    ref_parts = []
    for i, doc in enumerate(retrieval_result.documents, 1):
        # Ambil hanya bagian penting dari dokumen (potong di 600 karakter)
        content_excerpt = doc.content[:600] + "..." if len(doc.content) > 600 else doc.content
        ref_parts.append(
            f"[Referensi {i} — {doc.title} | Cosine: {doc.cosine_similarity:.3f} | Rerank: {doc.rerank_score:.4f}]\n"
            f"{content_excerpt}"
        )
    reference_docs = "\n\n".join(ref_parts)

    return USER_PROMPT_TEMPLATE.format(
        anomaly_score=anomaly_score,
        threshold=settings.anomaly_threshold,
        log_keys=", ".join(log_keys) if log_keys else "tidak terdeteksi",
        log_samples=log_samples,
        reference_docs=reference_docs,
        validation_note=retrieval_result.validation_note,
    )


def _parse_llm_response(response: str) -> dict:
    """
    Ekstrak field terstruktur dari respons LLM.
    Jika LLM tidak mengikuti format, fallback ke teks mentah.
    """
    fields = {
        "title": "",
        "summary": "",
        "context": "",
        "recommendation": "",
        "severity": "HIGH",
    }

    patterns = {
        "title": r"JUDUL:\s*(.+?)(?=\n[A-Z]+:|$)",
        "summary": r"RINGKASAN:\s*(.+?)(?=\n[A-Z]+:|$)",
        "context": r"KONTEKS:\s*(.+?)(?=\n[A-Z]+:|$)",
        "recommendation": r"REKOMENDASI:\s*(.+?)(?=\nSEVERITY:|$)",
        "severity": r"SEVERITY:\s*(CRITICAL|HIGH|MEDIUM|LOW)",
    }

    for field, pattern in patterns.items():
        match = re.search(pattern, response, re.DOTALL | re.IGNORECASE)
        if match:
            fields[field] = match.group(1).strip()

    # Fallback jika parsing gagal
    if not fields["title"]:
        fields["title"] = "Anomali Terdeteksi pada BGL Supercomputer"
    if not fields["summary"]:
        fields["summary"] = response[:200].strip()

    return fields


def _get_llm() -> ChatOpenAI:
    """Inisialisasi LLM client via OpenRouter (kompatibel OpenAI API)."""
    return ChatOpenAI(
        model=settings.openrouter_model,
        api_key=settings.openrouter_api_key,
        base_url="https://openrouter.ai/api/v1",
        temperature=0.3,
        max_tokens=800,
        default_headers={
            "HTTP-Referer": "https://github.com/deepl-fp",
            "X-Title": "BGL Log Anomaly Monitor",
        },
    )


async def run(
    anomaly_score: float,
    log_keys: list[str],
    log_sequence: list[str],
    retrieval_result: RetrievalResult,
) -> AlertDocument:
    """
    Jalankan Document Agent.

    Args:
        anomaly_score:    Skor anomali dari model
        log_keys:         Log keys dari output model
        log_sequence:     Raw logs dari time window
        retrieval_result: Output dari Retrieval Agent

    Returns:
        AlertDocument siap kirim ke Telegram dan disimpan ke DB
    """
    user_prompt = _build_user_prompt(
        anomaly_score, log_keys, log_sequence, retrieval_result
    )

    llm = _get_llm()
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=user_prompt),
    ]

    response = await llm.ainvoke(messages)
    raw_response = response.content

    parsed = _parse_llm_response(raw_response)

    return AlertDocument(
        title=parsed["title"],
        summary=parsed["summary"],
        context=parsed["context"],
        recommendation=parsed["recommendation"],
        severity=parsed["severity"],
        raw_llm_response=raw_response,
    )
