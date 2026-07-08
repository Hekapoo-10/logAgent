"""
Inference LogBERT + DeepSVDD — model asli hasil training.

Output:
    {anomaly_score, is_anomaly, log_keys, window_id, timestamp}
yang langsung dikonsumsi retrieval_agent, document_agent, dan FastAPI.

Model dimuat sekali (lazy) saat pemanggilan pertama.
"""
import uuid
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

import numpy as np
import torch
from drain3 import TemplateMiner
from drain3.template_miner_config import TemplateMinerConfig
from drain3.file_persistence import FilePersistence
from transformers import AutoModel, AutoTokenizer   # Auto → dukung BERT & DistilBERT

from src.model.svdd import DeepSVDDNet, anomaly_scores

_ROOT = Path(__file__).resolve().parents[2]
_MODELS = _ROOT / "models"
_LOGBERT_DIR = _MODELS / "logbert"
_SVDD_MODEL = _MODELS / "svdd.pt"
_DRAIN_STATE = _MODELS / "drain3_state.bin"

MAX_LENGTH = 256
MAX_LOG_KEYS = 128
THRESHOLD = 0.069  # kalibrasi Youden's J pada test set (BERT 20-epoch, AUC 0.96)
LOGKEY_PREFIX = "LOGKEY_"          # harus sama dengan config saat training (MLKP)

_DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


def _extract_content(line: str) -> str:
    """
    Ambil field 'content' yang sama seperti saat training.

    Baris BGL mentah punya 8+ field; content = field ke-9 (indeks 8).
    Dikenali dari field ke-2 yang berupa Unix timestamp (angka).
    Jika input sudah berupa content saja (bukan baris mentah), pakai apa adanya.
    """
    parts = line.strip().split(None, 8)
    if len(parts) >= 9 and parts[1].isdigit():
        return parts[8]
    return line.strip()


@lru_cache(maxsize=1)
def _load():
    """Muat semua artefak model sekali saja."""
    for p in (_LOGBERT_DIR, _SVDD_MODEL, _DRAIN_STATE):
        if not p.exists():
            raise FileNotFoundError(
                f"Artefak model tidak ditemukan: {p}\n"
                "Jalankan pipeline training di notebooks/train_pipeline.ipynb terlebih dahulu."
            )

    tokenizer = AutoTokenizer.from_pretrained(_LOGBERT_DIR)
    bert = AutoModel.from_pretrained(_LOGBERT_DIR).eval().to(_DEVICE)

    # DeepSVDD PyTorch murni
    ckpt = torch.load(_SVDD_MODEL, map_location=_DEVICE)
    svdd = DeepSVDDNet(ckpt["in_dim"]).to(_DEVICE).eval()
    svdd.load_state_dict(ckpt["state_dict"])
    center = ckpt["center"]
    score_range = {"min": ckpt["score_min"], "max": ckpt["score_max"]}

    # Pakai state Drain3 yang SAMA dengan training agar Log Key konsisten
    cfg = TemplateMinerConfig()
    cfg.drain_sim_th = 0.4
    cfg.drain_depth = 4
    miner = TemplateMiner(persistence_handler=FilePersistence(str(_DRAIN_STATE)), config=cfg)
    return tokenizer, bert, svdd, center, score_range, miner


def predict(log_sequence: list[str], window_id: str = None, timestamp: str = None) -> dict:
    """
    Prediksi anomali untuk satu window log.

    Args:
        log_sequence: baris log mentah dalam satu time window
        window_id, timestamp: opsional; dibuat otomatis jika tidak diberikan
    """
    tokenizer, bert, svdd, center, score_range, miner = _load()

    # 1. Drain3 → Log Key (match_only agar tidak mengubah state hasil training)
    #    Preprocessing HARUS sama dengan training: Drain3 dilatih pada field
    #    content (p[8]), bukan baris mentah lengkap.
    log_keys = []
    for line in log_sequence:
        cluster = miner.match(_extract_content(line))
        log_keys.append(str(cluster.cluster_id) if cluster else "UNK")

    # 2. Embedding CLS dari LogBERT (format token MLKP: LOGKEY_<id>)
    text = " ".join(f"{LOGKEY_PREFIX}{k}" for k in log_keys[:MAX_LOG_KEYS])
    enc = tokenizer(text, return_tensors="pt", truncation=True,
                    max_length=MAX_LENGTH).to(_DEVICE)
    with torch.no_grad():
        emb = bert(**enc).last_hidden_state[:, 0, :].cpu().numpy()

    # 3. DeepSVDD → skor mentah (jarak ke pusat) → normalisasi ke [0, 1]
    raw = float(anomaly_scores(svdd, center, emb, _DEVICE)[0])
    lo, hi = score_range["min"], score_range["max"]
    score = float(np.clip((raw - lo) / (hi - lo + 1e-9), 0.0, 1.0))

    return {
        "anomaly_score": round(score, 4),
        "is_anomaly": score >= THRESHOLD,
        "log_keys": list(dict.fromkeys(log_keys))[:10],   # unik, maks 10
        "window_id": window_id or f"win_{uuid.uuid4().hex[:12]}",
        "timestamp": timestamp or datetime.now(timezone.utc).isoformat(),
    }
