"""
Konfigurasi terpusat untuk pipeline training LogBERT + DeepSVDD.
Semua path dan hyperparameter dikumpulkan di sini agar mudah diubah.

Dituning untuk RTX 4050 Laptop (6 GB VRAM).
"""
from pathlib import Path

# ─── Paths ─────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[2]        # C:\Users\ASUS\Documents\DeepL_FP
DATA = ROOT / "data"
MODELS = ROOT / "models"
RESULTS = ROOT / "results"

RAW_LOG      = DATA / "BGL.log"                    # input mentah dari LOGHUB
RAW_DF       = DATA / "bgl_raw.pkl"                # hasil 1_load (pickle, anti-pyarrow)
PARSED_DF    = DATA / "bgl_parsed.pkl"             # hasil 2_parse
WINDOWS_PKL  = DATA / "windows.pkl"                # hasil 3_window
TRAIN_PKL    = DATA / "train.pkl"                  # hasil 4_split
TEST_PKL     = DATA / "test.pkl"

LOGBERT_DIR  = MODELS / "logbert"                  # hasil 5_train_logbert
SVDD_MODEL   = MODELS / "svdd.pt"                   # hasil 6 (net+center+range, torch murni)
DRAIN_STATE  = MODELS / "drain3_state.bin"         # state parser (WAJIB utk inference)

# ─── Preprocessing ─────────────────────────────────────────────────────────────
WINDOW_MINUTES = 5                                 # ukuran sliding window
MAX_LOG_KEYS   = 128                               # potong sequence agar muat max_length

# ─── Model / Training (aman untuk 6 GB VRAM) ───────────────────────────────────
BASE_MODEL       = "bert-base-uncased"             # BERT penuh (kapasitas lebih besar)
LOGKEY_PREFIX    = "LOGKEY_"                        # tiap Log Key jadi 1 token → MLM = MLKP
MAX_LENGTH       = 256
BATCH_SIZE       = 16                              # T4 Colab 15GB sanggup BERT-base
GRAD_ACCUM       = 1
EPOCHS           = 20
MLM_PROBABILITY  = 0.15
FP16             = True                            # hemat VRAM di GPU NVIDIA

# ─── Split ─────────────────────────────────────────────────────────────────────
TRAIN_RATIO = 0.7                                  # 70% window normal untuk training
SEED = 42

# ─── Deteksi ───────────────────────────────────────────────────────────────────
THRESHOLD = 0.069                                  # ambang anomaly_score kalibrasi test set (Youden's J)
SVDD_EPOCHS = 100

for _d in (DATA, MODELS, RESULTS):
    _d.mkdir(parents=True, exist_ok=True)
