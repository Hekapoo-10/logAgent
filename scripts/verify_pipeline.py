"""
Verification script untuk Phase 3 (model ASLI).
Test end-to-end pipeline: predict (LogBERT+DeepSVDD) → Retrieval Agent → Document Agent.

Prasyarat:
- Model sudah dilatih: models/logbert/, models/svdd.pt, models/drain3_state.bin
- Dataset di data/BGL.log (untuk mengambil window uji nyata)
- Dokumen RAG sudah teringest (Phase 2)
- OPENROUTER_API_KEY valid di .env, PostgreSQL berjalan
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule

from src.database.connection import AsyncSessionLocal, engine
from src.model.predict import predict
from src.agents import retrieval_agent, document_agent

console = Console()

_BGL_LOG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "BGL.log")


def load_real_windows(scan_lines: int = 200_000):
    """
    Ambil window BGL NYATA dari dataset: satu window normal & satu window anomali.
    Window anomali dipilih yang paling banyak baris anomalinya (paling jelas menyimpang).
    """
    import pandas as pd

    rows = []
    with open(_BGL_LOG, encoding="utf-8", errors="ignore") as f:
        for i, line in enumerate(f):
            if i >= scan_lines:
                break
            p = line.strip().split(None, 8)
            if len(p) < 9:
                continue
            rows.append({"raw": line.strip(), "is_anom": p[0] != "-", "ts": int(p[1])})

    df = pd.DataFrame(rows)
    df["win"] = df["ts"] // 300
    normal_win, anom_win, anom_score = None, None, -1
    for _, g in df.groupby("win"):
        if len(g) < 30:
            continue
        n_anom = int(g["is_anom"].sum())
        if n_anom == 0 and normal_win is None:
            normal_win = g["raw"].tolist()
        elif n_anom > anom_score:
            anom_score, anom_win = n_anom, g["raw"].tolist()
    return normal_win, anom_win


async def test_normal_log(normal_win):
    """Window normal seharusnya TIDAK memicu pipeline (is_anomaly = False)."""
    result = predict(normal_win)
    is_ok = not result["is_anomaly"]
    console.print(
        f"  {'[green]✅' if is_ok else '[red]❌'} Normal log tidak dianggap anomali "
        f"(score={result['anomaly_score']}, is_anomaly={result['is_anomaly']})"
    )
    return is_ok


async def test_anomaly_pipeline(anom_win):
    """Window anomali harus memicu full pipeline dan menghasilkan AlertDocument."""
    errors = []

    # Step 1: predict()
    console.print("\n  [bold]Step 1 — predict()[/bold]")
    result = predict(anom_win)
    console.print(f"  anomaly_score : {result['anomaly_score']}")
    console.print(f"  is_anomaly    : {result['is_anomaly']}")
    console.print(f"  log_keys      : {result['log_keys']}")
    console.print(f"  window_id     : {result['window_id']}")

    if not result["is_anomaly"]:
        errors.append("predict() tidak mendeteksi anomali pada window anomali nyata")
        console.print("  [red]❌ Seharusnya is_anomaly=True[/red]")
        return False, errors
    console.print("  [green]✅ is_anomaly=True — pipeline akan dilanjutkan[/green]")

    # Step 2: Retrieval Agent
    console.print("\n  [bold]Step 2 — Retrieval Agent[/bold]")
    async with AsyncSessionLocal() as db:
        retrieval = await retrieval_agent.run(
            log_keys=result["log_keys"],
            log_sequence=anom_win,
            anomaly_score=result["anomaly_score"],
            db=db,
        )

    # Tampilkan perbandingan Stage 1 (cosine) vs Stage 2 (rerank)
    from rich.columns import Columns
    from rich.table import Table as RichTable

    before_table = RichTable(title="Stage 1 — Cosine (ST)", show_header=True, header_style="bold yellow")
    before_table.add_column("Rank", width=5)
    before_table.add_column("Dokumen", width=30)
    before_table.add_column("Score", width=7)
    for c in retrieval.candidates_before_rerank:
        before_table.add_row(str(c["rank"]), c["title"][:30], f"{c['cosine_similarity']:.3f}")

    rerank_label = "Stage 2 — Nemotron Rerank" if retrieval.rerank_performed else "Stage 2 — FALLBACK (cosine)"
    after_table = RichTable(title=rerank_label, show_header=True, header_style="bold green")
    after_table.add_column("Rank", width=6)
    after_table.add_column("Dokumen", width=30)
    after_table.add_column("Rerank", width=8)
    after_table.add_column("Cosine", width=7)
    for doc in retrieval.documents:
        arrow = "↑" if doc.final_rank < doc.original_rank else ("↓" if doc.final_rank > doc.original_rank else "=")
        after_table.add_row(
            f"{doc.final_rank} {arrow}",
            doc.title[:30],
            f"{doc.rerank_score:.4f}",
            f"{doc.cosine_similarity:.3f}",
        )

    console.print(Columns([before_table, after_table]))
    console.print(f"\n  Rerank performed : {'✅ Ya' if retrieval.rerank_performed else '⚠️ Tidak (fallback)'}")
    console.print(f"  Validasi         : {'✅' if retrieval.is_context_valid else '⚠️'} {retrieval.validation_note}")

    if not retrieval.documents:
        errors.append("Retrieval Agent tidak menemukan dokumen")
        return False, errors
    console.print("  [green]✅ Retrieval Agent berhasil[/green]")

    # Step 3: Document Agent
    console.print("\n  [bold]Step 3 — Document Agent (memanggil Nemotron via OpenRouter)[/bold]")
    console.print("  [dim]Menunggu respons LLM...[/dim]")

    try:
        alert = await document_agent.run(
            anomaly_score=result["anomaly_score"],
            log_keys=result["log_keys"],
            log_sequence=anom_win,
            retrieval_result=retrieval,
        )
    except Exception as e:
        errors.append(f"Document Agent error: {e}")
        console.print(f"  [red]❌ Error: {e}[/red]")
        return False, errors

    console.print("  [green]✅ Document Agent berhasil[/green]")

    # Tampilkan hasil alert
    console.print()
    console.print(Rule("[bold cyan]HASIL ALERT DOCUMENT[/bold cyan]"))
    console.print(Panel(
        f"[bold]{alert.title}[/bold]\n\n"
        f"[yellow]RINGKASAN:[/yellow]\n{alert.summary}\n\n"
        f"[yellow]KONTEKS:[/yellow]\n{alert.context}\n\n"
        f"[yellow]REKOMENDASI:[/yellow]\n{alert.recommendation}\n\n"
        f"[bold red]SEVERITY: {alert.severity}[/bold red]",
        border_style="cyan",
    ))

    return True, []


async def main():
    console.print("\n[bold cyan]═══ Phase 3 — Pipeline Verification (MODEL ASLI) ═══[/bold cyan]\n")

    console.print("[dim]Memuat window BGL nyata dari dataset...[/dim]")
    normal_win, anom_win = load_real_windows()
    if normal_win is None or anom_win is None:
        console.print("[red]❌ Gagal mengambil window uji dari data/BGL.log[/red]")
        sys.exit(1)
    console.print(f"[dim]Window normal: {len(normal_win)} baris | Window anomali: {len(anom_win)} baris[/dim]\n")

    all_passed = True

    # Test 1: Normal log tidak memicu anomali
    console.print(Rule("[bold]Test 1: Normal Window[/bold]"))
    ok = await test_normal_log(normal_win)
    if not ok:
        all_passed = False

    # Test 2: Full pipeline dengan anomaly log
    console.print()
    console.print(Rule("[bold]Test 2: Anomaly Pipeline (Full)[/bold]"))
    ok, errors = await test_anomaly_pipeline(anom_win)
    if not ok:
        all_passed = False
        for err in errors:
            console.print(f"  [red]• {err}[/red]")

    console.print()
    if all_passed:
        console.print("[bold green]✅ Phase 3 COMPLETE — Lanjut ke Phase 4![/bold green]\n")
    else:
        console.print("[bold red]❌ Ada langkah yang gagal. Cek output di atas.[/bold red]\n")
        sys.exit(1)

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
