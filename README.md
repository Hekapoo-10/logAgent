# BGL Supercomputer Log Anomaly Monitoring System

Final Project RKK304 Deep Learning — Kelompok 12
Program Studi Teknik Robotika dan Kecerdasan Buatan, Universitas Airlangga 2026

Sistem deteksi anomali log supercomputer BGL yang **menjelaskan** setiap anomali:
LogBERT + DeepSVDD untuk deteksi, lalu pipeline RAG agentic untuk menghasilkan
alert terstruktur yang dikirim ke Telegram.

```
Raw BGL Log → Drain3 → Sliding Window → LogBERT + DeepSVDD → (anomali?)
                                                                 │
        Telegram ← Document Agent (Nemotron 120B) ← Retrieval Agent (pgvector + Nemotron rerank)
```

## Hasil

| Aspek | Metrik | Nilai |
|-------|--------|-------|
| Deteksi | ROC-AUC | 0.9605 |
| Deteksi | F1 (anomali) | 0.819 |
| Deteksi | Akurasi | 0.919 |
| RAG | Faithfulness | 0.554 |
| RAG | Context Precision | 1.000 |

## Arsitektur

- **Deteksi:** BERT-base (fine-tune MLKP) + DeepSVDD (PyTorch), threshold 0.069 (Youden's J)
- **Database:** PostgreSQL 15 + pgvector (HNSW), 12 dokumen knowledge base
- **Retrieval Agent:** two-stage — cosine (all-MiniLM-L6-v2, top-5) → Nemotron rerank (top-3)
- **Document Agent:** Nemotron-3 Super 120B (via OpenRouter)
- **Backend:** FastAPI (async) — orkestrator terpusat
- **Delivery:** Telegram Bot + UI demo (`GET /`)

## Tech Stack

Drain3 · PyTorch · HuggingFace Transformers · PostgreSQL + pgvector ·
sentence-transformers · Nemotron (OpenRouter) · LangChain · FastAPI ·
SQLAlchemy (async) · python-telegram-bot · Docker

## Struktur Proyek

```
src/
├── agents/        # Retrieval Agent + Document Agent
├── api/           # FastAPI (routes: predict, alerts, analyze/UI)
├── bot/           # Telegram delivery
├── model/         # predict.py (inference), svdd.py (DeepSVDD)
├── rag/           # embedder + 12 dokumen knowledge base
├── database/      # SQLAlchemy models + koneksi
└── config/        # settings (Pydantic)
scripts/           # setup, verifikasi, ingest, evaluasi RAG
notebooks/         # training (Colab & lokal) + evaluasi RAGAS
```

## Setup

**Prasyarat:** Docker, Conda, model & dataset (lihat di bawah).

```bash
# 1. Environment
conda create -n deepl-fp python=3.11 -y
conda activate deepl-fp
pip install -r requirements.txt

# 2. Konfigurasi — salin .env.example → .env, isi API key & token
cp .env.example .env

# 3. Database
docker compose up -d
python scripts/init_db.py
python scripts/ingest_rag.py

# 4. Jalankan
uvicorn src.api.main:app --reload
# UI: http://localhost:8000/   |   Swagger: http://localhost:8000/docs
```

## Model & Dataset (tidak disertakan — terlalu besar)

| Artefak | Ukuran | Lokasi |
|---------|--------|--------|
| Dataset `BGL.log` | ~709 MB | [LOGHUB / Zenodo](https://github.com/logpai/loghub) → taruh di `data/BGL.log` |
| Model terlatih `models/` | ~420 MB | *(host sendiri: Google Drive / HuggingFace)* |

Untuk melatih ulang model: jalankan `notebooks/train_colab.ipynb` di Google Colab (GPU),
lalu ekstrak `models.zip` ke `models/`.

## Konfigurasi (.env)

Lihat `.env.example` untuk daftar lengkap. Yang wajib diisi:
`DATABASE_URL`, `OPENROUTER_API_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`.
