"""
Tahap 1 evaluasi RAG — kumpulkan data.

Jalankan Retrieval + Document Agent pada N window anomali NYATA, DENGAN dan
TANPA rerank, lalu simpan (query, contexts, answer) ke JSON.

Catatan desain:
- TIDAK memanggil src.model.predict (torch/BERT) — itu memicu segfault sporadis
  di env ini, dan untuk evaluasi RAG kita tidak butuh skor model. Query retrieval
  dibangun dari baris log; anomaly_score dipakai placeholder untuk prompt.
- Simpan INCREMENTAL (tiap window) agar crash tidak menghilangkan progres.

Prasyarat: PostgreSQL jalan, RAG teringest, OPENROUTER_API_KEY valid.
Jalankan:  python scripts/collect_rag_eval.py
"""
import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

from src.agents import retrieval_agent, document_agent
from src.database.connection import AsyncSessionLocal, engine

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BGL_LOG = os.path.join(ROOT, "data", "BGL.log")
OUT = os.path.join(ROOT, "results", "rag_eval_data.json")

N_WINDOWS = 25
SCAN_LINES = 1_500_000
PLACEHOLDER_SCORE = 0.9   # dipakai di prompt Document Agent (bukan skor model asli)


def load_anomaly_windows(n: int) -> list[list[str]]:
    rows = []
    with open(BGL_LOG, encoding="utf-8", errors="ignore") as f:
        for i, line in enumerate(f):
            if i >= SCAN_LINES:
                break
            p = line.strip().split(None, 8)
            if len(p) < 9:
                continue
            rows.append({"raw": line.strip(), "is_anom": p[0] != "-", "ts": int(p[1])})

    df = pd.DataFrame(rows)
    df["win"] = df["ts"] // 300
    windows = []
    for _, g in df.groupby("win"):
        if g["is_anom"].any() and 15 <= len(g) <= 150:
            windows.append(g["raw"].tolist())
        if len(windows) >= n:
            break
    return windows


async def main():
    if not os.path.exists(BGL_LOG):
        raise FileNotFoundError(f"{BGL_LOG} tidak ada.")

    windows = load_anomaly_windows(N_WINDOWS)
    print(f"Mengumpulkan {len(windows)} window anomali...", flush=True)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)

    records = []
    async with AsyncSessionLocal() as db:
        for i, lines in enumerate(windows, 1):
            try:
                # DENGAN rerank → contexts + Document Agent (jawaban final)
                rr = await retrieval_agent.run([], lines, PLACEHOLDER_SCORE, db, use_rerank=True)
                if not rr.documents:
                    print(f"  {i}: dilewati (tidak ada dokumen)", flush=True)
                    continue
                alert = await document_agent.run(PLACEHOLDER_SCORE, [], lines, rr)
                answer = "\n".join([alert.title, alert.summary, alert.context, alert.recommendation])

                # TANPA rerank → contexts saja (cosine top-k)
                nr = await retrieval_agent.run([], lines, PLACEHOLDER_SCORE, db, use_rerank=False)

                records.append({
                    "query": rr.query_used,
                    "contexts_with_rerank": [d.content for d in rr.documents],
                    "contexts_no_rerank": [d.content for d in nr.documents],
                    "answer": answer,
                })
                # SIMPAN INCREMENTAL — crash tidak menghilangkan progres
                with open(OUT, "w", encoding="utf-8") as f:
                    json.dump(records, f, ensure_ascii=False, indent=2)
                print(f"  {i}/{len(windows)} selesai (total tersimpan: {len(records)})", flush=True)
            except Exception as e:
                print(f"  {i}: ERROR {str(e)[:100]}", flush=True)

    await engine.dispose()
    print(f"\n✅ {len(records)} sampel tersimpan → {OUT}")


if __name__ == "__main__":
    asyncio.run(main())
