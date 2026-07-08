"""
Tahap 2 evaluasi RAG — jalankan RAGAS (metrik LLM-only, aman dari segfault torch).

Metrik:
  • Faithfulness      — apakah alert setia pada dokumen konteks (tak halusinasi)
  • Context Precision — apakah dokumen yang diretrieval relevan
                        → dihitung DENGAN vs TANPA rerank untuk bukti two-stage

Judge: OpenRouter (settings.openrouter_judge_model), model BERBEDA dari generator
(Nemotron) untuk menghindari self-preference bias.

Catatan: Response Relevancy (butuh embedding lokal/torch) sengaja tidak dipakai
karena RAGAS mengevaluasi paralel → torch multi-thread menyebabkan segfault di env ini.

Prasyarat: jalankan scripts/collect_rag_eval.py dulu (menghasilkan JSON).
Jalankan:  python scripts/evaluate_rag.py
"""
import json
import os
import sys
import warnings

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
warnings.filterwarnings("ignore")

from langchain_openai import ChatOpenAI
from ragas import EvaluationDataset, evaluate
from ragas.llms import LangchainLLMWrapper
from ragas.metrics import Faithfulness, LLMContextPrecisionWithoutReference
from ragas.run_config import RunConfig

from src.config.settings import settings

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "results", "rag_eval_data.json")

# WAJIB serial (max_workers=1): eksekusi paralel memicu segfault karena
# RAGAS memakai pandas/pyarrow antar-thread dan pyarrow di env ini tidak stabil.
RUN_CFG = RunConfig(max_workers=1, timeout=120)


def _mean(result, key_options):
    """Rata-rata skor dari result.scores (list dict) — TANPA pandas/pyarrow
    yang tidak stabil di env ini."""
    for k in key_options:
        vals = [s[k] for s in result.scores if k in s and s[k] is not None]
        if vals:
            return sum(vals) / len(vals)
    return None


def main():
    if not os.path.exists(DATA):
        raise FileNotFoundError(f"{DATA} tidak ada. Jalankan scripts/collect_rag_eval.py dulu.")

    data = json.load(open(DATA, encoding="utf-8"))
    print(f"Memuat {len(data)} sampel | Judge: {settings.openrouter_judge_model}\n")

    judge = LangchainLLMWrapper(ChatOpenAI(
        api_key=settings.openrouter_api_key,
        base_url="https://openrouter.ai/api/v1",
        model=settings.openrouter_judge_model,
        temperature=0,
    ))

    # ── Faithfulness (generation, output pipeline dengan rerank) ────────────
    print("[1/3] Faithfulness (generation)...")
    gen_ds = EvaluationDataset.from_list([
        {"user_input": d["query"], "retrieved_contexts": d["contexts_with_rerank"], "response": d["answer"]}
        for d in data
    ])
    gen = evaluate(gen_ds, metrics=[Faithfulness()], llm=judge, run_config=RUN_CFG)
    faith = _mean(gen, ["faithfulness"])

    # ── Context Precision: dengan vs tanpa rerank ─────────────────────────
    def ctx_ds(key):
        return EvaluationDataset.from_list([
            {"user_input": d["query"], "retrieved_contexts": d[key], "response": d["answer"]}
            for d in data
        ])

    print("[2/3] Context Precision — DENGAN rerank...")
    cp_wr = evaluate(ctx_ds("contexts_with_rerank"),
                     metrics=[LLMContextPrecisionWithoutReference()], llm=judge, run_config=RUN_CFG)
    print("[3/3] Context Precision — TANPA rerank...")
    cp_nr = evaluate(ctx_ds("contexts_no_rerank"),
                     metrics=[LLMContextPrecisionWithoutReference()], llm=judge, run_config=RUN_CFG)
    key = ["llm_context_precision_without_reference"]
    cp_with = _mean(cp_wr, key)
    cp_without = _mean(cp_nr, key)

    # ── Laporan ────────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("           HASIL EVALUASI RAGAS")
    print("=" * 60)
    print(f"Sampel        : {len(data)} window anomali")
    print(f"Judge model   : {settings.openrouter_judge_model}")
    print("-" * 60)
    print("GENERATION (output Document Agent / Nemotron):")
    print(f"  Faithfulness       : {faith:.4f}   (setia pada konteks, tak halusinasi)")
    print("-" * 60)
    print("RETRIEVAL (Context Precision) — bukti two-stage:")
    print(f"  TANPA rerank (cosine) : {cp_without:.4f}")
    print(f"  DENGAN rerank         : {cp_with:.4f}")
    delta = (cp_with - cp_without) if (cp_with is not None and cp_without is not None) else 0
    arrow = "lebih baik" if delta > 0 else ("lebih buruk" if delta < 0 else "sama")
    print(f"  Selisih               : {delta:+.4f}  ({arrow})")
    print("=" * 60)

    out = os.path.join(ROOT, "results", "ragas_summary.json")
    json.dump({
        "n_samples": len(data),
        "judge_model": settings.openrouter_judge_model,
        "faithfulness": faith,
        "context_precision_with_rerank": cp_with,
        "context_precision_no_rerank": cp_without,
    }, open(out, "w", encoding="utf-8"), indent=2)
    print(f"\nRingkasan -> {out}")


if __name__ == "__main__":
    main()
