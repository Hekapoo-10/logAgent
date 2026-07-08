"""
Verification script untuk Phase 1.
Jalankan setelah init_db.py berhasil.
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from rich.console import Console
from rich.table import Table

from src.database.connection import engine

console = Console()


async def run_checks():
    checks = []

    async with engine.connect() as conn:
        # 1. pgvector extension aktif di database
        r = await conn.execute(text(
            "SELECT COUNT(*) FROM pg_extension WHERE extname = 'vector'"
        ))
        ok = r.scalar() > 0
        checks.append(("pgvector extension active", ok,
                        "Active" if ok else "Run: CREATE EXTENSION vector"))

        # 2. Tabel documents ada
        r = await conn.execute(text(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_name = 'documents' AND table_schema = 'public'"
        ))
        ok = r.scalar() > 0
        checks.append(("Table 'documents' exists", ok,
                        "OK" if ok else "Run: python scripts/init_db.py"))

        # 3. Tabel alert_history ada
        r = await conn.execute(text(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_name = 'alert_history' AND table_schema = 'public'"
        ))
        ok = r.scalar() > 0
        checks.append(("Table 'alert_history' exists", ok,
                        "OK" if ok else "Run: python scripts/init_db.py"))

        # 4. HNSW index pada documents.embedding ada
        r = await conn.execute(text(
            "SELECT COUNT(*) FROM pg_indexes "
            "WHERE indexname = 'documents_embedding_hnsw_idx'"
        ))
        ok = r.scalar() > 0
        checks.append(("HNSW index on documents.embedding", ok,
                        "OK" if ok else "Run: python scripts/init_db.py"))

        # 5. Kolom embedding bertipe vector(384)
        r = await conn.execute(text(
            "SELECT udt_name FROM information_schema.columns "
            "WHERE table_name = 'documents' AND column_name = 'embedding'"
        ))
        row = r.fetchone()
        ok = row is not None and "vector" in str(row[0]).lower()
        checks.append(("documents.embedding type = vector(384)", ok,
                        f"Type: {row[0] if row else 'NOT FOUND'}"))

    return checks


async def main():
    console.print("\n[bold cyan]═══ Phase 1 Verification ═══[/bold cyan]\n")

    try:
        checks = await run_checks()
    except Exception as e:
        console.print(f"[bold red]❌ Cannot connect to database: {e}[/bold red]")
        console.print("[yellow]Pastikan Docker Compose berjalan: docker compose up -d[/yellow]")
        sys.exit(1)

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Check", style="cyan", width=40)
    table.add_column("Status", width=12)
    table.add_column("Detail", width=40)

    all_passed = True
    for name, ok, detail in checks:
        status = "[green]✅ PASS[/green]" if ok else "[red]❌ FAIL[/red]"
        table.add_row(name, status, detail)
        if not ok:
            all_passed = False

    console.print(table)

    if all_passed:
        console.print("\n[bold green]✅ Phase 1 COMPLETE — Lanjut ke Phase 2![/bold green]\n")
    else:
        console.print("\n[bold red]❌ Ada yang perlu diperbaiki. Jalankan:[/bold red]")
        console.print("   python scripts/init_db.py\n")
        sys.exit(1)

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
