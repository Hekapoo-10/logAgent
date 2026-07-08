# Pipeline Training LogBERT + DeepSVDD

Melatih model deteksi anomali dari dataset BGL. Dituning untuk **RTX 4050 (6 GB VRAM)**.

Training dijalankan lewat notebook: **`notebooks/train_pipeline.ipynb`**.
Folder ini hanya menyimpan `config.py` (parameter terpusat yang diimpor notebook).

## Prasyarat

```bash
conda activate deepl-fp
pip install drain3 transformers matplotlib nbformat ipykernel

# WAJIB: PyTorch versi CUDA (bukan +cpu)
python -c "import torch; print(torch.cuda.is_available())"   # harus True
```

> Catatan dependency (khusus lingkungan Windows ini):
> - **DeepSVDD** = PyTorch murni (`src/model/svdd.py`), **bukan** pyod → hindari numba yang diblokir Windows Application Control.
> - **Training LogBERT** = loop PyTorch manual, **bukan** `transformers.Trainer` → Trainer meng-import `datasets`→`aiohttp` yang gagal karena SSL Windows cert store rusak.
> - Karena itu `datasets` dan `pyod` **tidak** diinstall.

Download `BGL.log` dari [LOGHUB](https://github.com/logpai/loghub) (folder BGL) → taruh di `data/BGL.log`.

## Menjalankan

1. Buka `notebooks/train_pipeline.ipynb` (VSCode / Jupyter).
2. Cell **Setup** — atur mode verifikasi:
   - `LIMIT = 50000`, `SMOKE = True`  → uji cepat, cek program tanpa error.
   - `LIMIT = None`,  `SMOKE = False` → training penuh.
3. Jalankan cell berurutan (Tahap 1 → 6).

## Tahapan (di dalam notebook)

| Tahap | Beban | Output |
|-------|-------|--------|
| 1 Load BGL.log | CPU | `data/bgl_raw.parquet` |
| 2 Parse Drain3 | CPU | `data/bgl_parsed.parquet`, `models/drain3_state.bin` |
| 3 Sliding window | CPU | `data/windows.pkl` |
| 4 Split train/test | CPU | `data/train.pkl`, `data/test.pkl` |
| 5 Train LogBERT | **GPU** | `models/logbert/` |
| 6 Train DeepSVDD | GPU | `models/svdd.pkl`, `models/score_range.pkl` |

## Setelah Training — Ganti Stub → Model Asli

Artefak dibutuhkan: `models/logbert/`, `models/svdd.pkl`,
`models/score_range.pkl`, `models/drain3_state.bin`.

`src/model/predict.py` sudah siap memuatnya. Tinggal ubah impor di
`scripts/verify_pipeline.py` baris 19:

```python
from src.model.stub import ...       # lama
from src.model.predict import predict # baru
```

Semua parameter ada di `scripts/training/config.py`.
