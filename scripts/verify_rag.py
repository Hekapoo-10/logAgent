"""
Verification script untuk Phase 2.
Cek jumlah dokumen dan test similarity search dengan query dummy.
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from rich.console import Console
from rich.table import Table

from src.database.connection import engine
from src.rag.embedder import embed_text

console = Console()

# Query test: simulasikan log keys dari anomali memory error
TEST_QUERY = "MEMORY_CE RAS ECC correctable error DRAM processor"
EXPECTED_TOP_RESULT = "memory"  # kata yang harus ada di dokumen teratas


async def run_checks():
    checks = []

    async with engine.connect() as conn:
        # 1. Cek ada dokumen di tabel
        r = await conn.execute(text("SELECT COUNT(*) FROM documents"))
        count = r.scalar()
        ok = count >= 10
        checks.append(("Minimum 10 dokumen di tabel", ok,
                        f"{count} dokumen ditemukan"))

        # 2. Cek semua dokumen punya embedding
        r = await conn.execute(text(
            "SELECT COUNT(*) FROM documents WHERE embedding IS NOT NULL"
        ))
        embedded = r.scalar()
        ok = embedded == count
        checks.append(("Semua dokumen punya embedding", ok,
                        f"{embedded}/{count} punya embedding"))

        # 3. Similarity search test
        query_vector = embed_text(TEST_QUERY)
        vector_str = "[" + ",".join(str(x) for x in query_vector) + "]"

        r = await conn.execute(text(f"""
            SELECT doc_metadata->>'title', doc_metadata->>'category',
                   1 - (embedding <=> '{vector_str}'::vector) AS similarity
            FROM documents
            ORDER BY embedding <=> '{vector_str}'::vector
            LIMIT 3
        """))
        rows = r.fetchall()
        ok = len(rows) > 0 and EXPECTED_TOP_RESULT in rows[0][0].lower()
        top_result = rows[0][0] if rows else "none"
        checks.append(("Similarity search berjalan", ok,
                        f"Top result: {top_result}"))

    return checks, rows if 'rows' in dir() else []


async def main():
    console.print("\n[bold cyan]═══ Phase 2 Verification ═══[/bold cyan]\n")

    try:
        checks, top_rows = await run_checks()
    except Exception as e:
        console.print(f"[bold red]❌ Error: {e}[/bold red]")
        sys.exit(1)

    # Tabel status
    status_table = Table(show_header=True, header_style="bold magenta")
    status_table.add_column("Check", style="cyan", width=40)
    status_table.add_column("Status", width=12)
    status_table.add_column("Detail", width=40)

    all_passed = True
    for name, ok, detail in checks:
        status = "[green]✅ PASS[/green]" if ok else "[red]❌ FAIL[/red]"
        status_table.add_row(name, status, detail)
        if not ok:
            all_passed = False

    console.print(status_table)

    # Tampilkan top-3 similarity search result
    if top_rows:
        console.print(f"\n[bold]Top-3 dokumen untuk query:[/bold] [italic]\"{TEST_QUERY}\"[/italic]")
        result_table = Table(show_header=True, header_style="bold blue")
        result_table.add_column("Rank", width=6)
        result_table.add_column("Dokumen", width=40)
        result_table.add_column("Kategori", width=25)
        result_table.add_column("Similarity", width=12)
        for i, (title, category, score) in enumerate(top_rows, 1):
            result_table.add_row(str(i), title, category or "-", f"{score:.4f}")
        console.print(result_table)

    if all_passed:
        console.print("\n[bold green]✅ Phase 2 COMPLETE — Lanjut ke Phase 3![/bold green]\n")
    else:
        console.print("\n[bold red]❌ Ada yang perlu diperbaiki. Jalankan:[/bold red]")
        console.print("   python scripts/ingest_rag.py\n")
        sys.exit(1)

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
