# Log Anomaly Monitoring System — Progress Tracker
> Final Project RKK304 Deep Learning — Kelompok 12
> Program Studi Teknik Robotika dan Kecerdasan Buatan, Universitas Airlangga 2026
> Stack: FastAPI · PostgreSQL + pgvector · LangChain · Nemotron · Telegram Bot

---

## Arsitektur Pipeline (Referensi Cepat)

```
Raw Log BGL
    ↓
[TEMAN] Drain3 → Log Key
    ↓
[TEMAN] Sliding Window (5 menit, ~562 log/sequence)
    ↓
[TEMAN] LogBERT + DeepSVDD → {anomaly_score, is_anomaly, log_keys, window_id, timestamp}
    ↓
is_anomaly == False → STOP
is_anomaly == True  → lanjut ↓
    ↓
[KITA] Retrieval Agent → similarity search pgvector + validasi konteks
    ↓
[KITA] Document Agent  → LLM Nemotron reasoning → dokumen alert terstruktur
    ↓
[KITA] FastAPI         → simpan ke alert_history, trigger Telegram
    ↓
[KITA] Telegram Bot    → push alert ke user (DELIVERY ONLY, bukan trigger)
```

**Threshold anomali: score >= 0.80**
**Tidak ada UI/dashboard — Telegram adalah satu-satunya delivery channel**

---

## Status Legenda
| Simbol | Arti |
|--------|------|
| ✅ | Selesai & sudah diverifikasi |
| 🔄 | Sedang dikerjakan |
| ⏳ | Belum dimulai (menunggu step sebelumnya) |
| ❌ | Gagal / ada error (harus diperbaiki sebelum lanjut) |
| ⚠️ | Perlu perhatian / ada catatan penting |

---

## PHASE 0 — Setup Environment ✅
> Selesai. Semua verifikasi lulus.

### Checklist
- [x] **0.1** Struktur folder proyek dibuat
- [x] **0.2** `PROGRESS.md` dibuat
- [x] **0.3** `docker-compose.yml` dibuat (PostgreSQL 15 + pgvector)
- [x] **0.4** `.env.example` dibuat (threshold dikoreksi ke 0.80)
- [x] **0.5** `requirements.txt` dibuat (+ scikit-learn, matplotlib, seaborn)
- [x] **0.6** `.gitignore` dibuat
- [x] **0.7** `scripts/verify_setup.py` dibuat
- [x] **0.8** Conda environment `deepl-fp` (Python 3.11) dibuat & aktif
- [x] **0.9** Dependencies terinstall (SQLAlchemy di-pin ke 2.0.35)
- [x] **0.10** Docker Compose up — PostgreSQL 15 berjalan
- [x] **0.11** `.env` diisi dengan nilai nyata
- [x] **0.12** Verifikasi Phase 0: semua ✅ PASS

---

## PHASE 1 — Database Layer ✅
> **Prasyarat:** Phase 0 ✅
> **Tujuan:** Tabel `documents` dan `alert_history` terbentuk di PostgreSQL, HNSW index aktif.

### Checklist
- [x] **1.1** `src/config/settings.py` — Pydantic settings dari .env
- [x] **1.2** `src/database/connection.py` — SQLAlchemy async engine + session
- [x] **1.3** `src/database/models.py` — Model tabel `documents` + `alert_history`
- [x] **1.4** `scripts/init_db.py` — Migration: pgvector + tabel + HNSW index
- [x] **1.5** `scripts/verify_db.py` — Script verifikasi Phase 1
- [x] **1.6** Migration dijalankan: `python scripts/init_db.py`
- [x] **1.7** Verifikasi: `python scripts/verify_db.py` — semua ✅ PASS

### Schema Database
| Tabel | Kolom Utama | Fungsi |
|-------|-------------|--------|
| `documents` | content, embedding vector(384), doc_metadata | Knowledge base RAG |
| `alert_history` | window_id, anomaly_score, log_keys[], retrieved_docs, alert_*, telegram_status | Audit trail pipeline |

### Verifikasi Phase 1 Selesai
```bash
python scripts/verify_db.py
# Semua harus ✅ PASS
```

---

## PHASE 2 — Knowledge Base RAG ✅
> **Prasyarat:** Phase 1 ✅ (tabel `documents` harus ada)
> **Tujuan:** Dokumen pola anomali BGL log teringested ke pgvector, siap di-query.

### Checklist
- [x] **2.1** 12 dokumen knowledge base ditulis di `src/rag/documents/`
- [x] **2.2** `src/rag/embedder.py` — embedding utility (sentence-transformers lokal)
- [x] **2.3** `scripts/ingest_rag.py` — ingest .md → embed → simpan ke tabel documents
- [x] **2.4** `scripts/verify_rag.py` — cek jumlah dokumen + test similarity search
- [x] **2.5** Ingest selesai: `python scripts/ingest_rag.py`
- [x] **2.6** Verifikasi: semua ✅ PASS (top result: Memory CE, similarity 0.54)

### Verifikasi Phase 2 Selesai
```bash
python scripts/verify_rag.py
```

---

## PHASE 3 — Retrieval Agent + Document Agent ✅
> **Prasyarat:** Phase 2 ✅
> **Tujuan:** Pipeline mock predict → Retrieval Agent → Document Agent berjalan end-to-end.

### Checklist
- [x] **3.1** `src/model/stub.py` — Mock `predict()` dengan output lengkap (+ window_id, timestamp)
- [x] **3.2** `src/agents/retrieval_agent.py` — Similarity search + validasi konteks
- [x] **3.3** `src/agents/document_agent.py` — LangChain + Nemotron + formatting alert
- [x] **3.4** `scripts/verify_pipeline.py` — Script verifikasi end-to-end
- [x] **3.5** Verifikasi pipeline: semua ✅ PASS. Alert dihasilkan Nemotron 3 Super 120B.

### Verifikasi Phase 3 Selesai
```bash
python scripts/verify_pipeline.py
```

---

## PHASE 4 — FastAPI Backend ✅
> **Prasyarat:** Phase 3 ✅
> **Tujuan:** API berjalan, pipeline bisa dipanggil via HTTP, alert_history tersimpan.

### Checklist
- [x] **4.1** `src/api/schemas.py` — Pydantic request/response schemas (format Opsi B)
- [x] **4.2** `src/api/main.py` — FastAPI app + CORS + request logging + error handler
- [x] **4.3** `src/api/routes/predict.py` — `POST /predict` (full pipeline)
- [x] **4.4** `src/api/routes/alerts.py` — `GET /alerts`, `GET /alerts/{id}`, `GET /health`
- [x] **4.5** Server berjalan: `uvicorn src.api.main:app --reload`
- [x] **4.6** Swagger dapat diakses di `/docs`
- [x] **4.7** `POST /predict` berhasil ditest

### Verifikasi Phase 4 Selesai
```bash
uvicorn src.api.main:app --reload
# Buka: http://localhost:8000/docs
```

---

## PHASE 5 — Telegram Bot 🔄
> **Prasyarat:** Phase 4 ✅
> **Tujuan:** Alert otomatis terkirim ke Telegram saat anomali terdeteksi.

### Checklist
- [x] **5.1** Telegram Bot Token didapat dari BotFather
- [x] **5.2** `src/bot/telegram.py` — `send_alert()` + bot command handlers
- [x] **5.3** Command `/start`, `/status`, `/history`, `/help`
- [x] **5.4** Format pesan HTML dengan emoji severity (🔴🟠🟡🟢)
- [x] **5.5** Bot diintegrasikan ke FastAPI lifespan sebagai background task
- [ ] **5.6** ⚠️ **[AKSI KAMU]** Isi `.env`: `TELEGRAM_CHAT_ID=<id_kamu>`
- [ ] **5.7** ⚠️ **[AKSI KAMU]** Restart server & test end-to-end via Swagger

### Verifikasi Phase 5 Selesai
```
Kirim request anomali → pesan masuk di Telegram ✅
```

---

## PHASE 6 — Evaluasi & Polish ⏳
> **Prasyarat:** Phase 5 ✅
> **Tujuan:** Sistem siap demo, evaluasi performa terdokumentasi.

### Checklist
- [ ] **6.1** Script evaluasi dengan scikit-learn (precision, recall, F1)
- [ ] **6.2** Visualisasi anomaly score over time (matplotlib/seaborn)
- [ ] **6.3** Test end-to-end dengan sample BGL dataset
- [ ] **6.4** Swagger API docs lengkap

---

## Catatan & Keputusan Teknis
| Tanggal | Catatan |
|---------|---------|
| 2026-06-15 | Proyek dimulai. Phase 0 selesai. |
| 2026-06-15 | Arsitektur dikoreksi: tidak ada UI/dashboard, hanya Telegram. Threshold 0.80. Tabel diubah: documents + alert_history. predict() output tambah window_id dan timestamp. |

---

## Error Log
| Phase | Error | Solusi |
|-------|-------|--------|
| - | - | - |
