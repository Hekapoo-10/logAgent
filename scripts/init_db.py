"""
Phase 1 — Database initialization script.
Jalankan SEKALI setelah Docker Compose up.

Urutan eksekusi:
1. Enable pgvector extension
2. Buat tabel: documents, alert_history
3. Buat HNSW index pada documents.embedding
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from rich.console import Console

from src.database.connection import engine, Base
from src.database.models import Document, AlertHistory  # noqa: F401

console = Console()


async def enable_pgvector(conn):
    await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    console.print("[green]✅ pgvector extension enabled[/green]")


async def create_tables(conn):
    await conn.run_sync(Base.metadata.create_all)
    console.print("[green]✅ Tables created: documents, alert_history[/green]")


async def create_hnsw_index(conn):
    # HNSW index untuk cosine similarity search pada kolom embedding
    # m=16        : koneksi per node — trade-off antara kecepatan build vs akurasi search
    # ef_construction=64 : kandidat saat build — lebih tinggi = lebih akurat, lebih lambat
    await conn.execute(text("""
        CREATE INDEX IF NOT EXISTS documents_embedding_hnsw_idx
        ON documents
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """))
    console.print("[green]✅ HNSW index created on documents.embedding[/green]")


async def main():
    console.print("\n[bold cyan]═══ Phase 1 — Database Initialization ═══[/bold cyan]\n")

    try:
        async with engine.begin() as conn:
            await enable_pgvector(conn)
            await create_tables(conn)
            await create_hnsw_index(conn)

        console.print("\n[bold green]✅ Database initialized successfully![/bold green]")
        console.print("[dim]Jalankan: python scripts/verify_db.py[/dim]\n")

    except Exception as e:
        console.print(f"\n[bold red]❌ Error: {e}[/bold red]\n")
        sys.exit(1)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
