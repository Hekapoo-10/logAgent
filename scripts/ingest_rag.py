"""
Phase 2 — RAG Knowledge Base ingest script.
Baca semua file .md dari src/rag/documents/, embed, simpan ke tabel documents.

Aman dijalankan ulang: dokumen yang sudah ada di DB tidak akan diduplikasi
(cek berdasarkan nama file di doc_metadata).
"""
import asyncio
import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from rich.console import Console
from rich.progress import track

from src.database.connection import AsyncSessionLocal, engine
from src.database.models import Document
from src.rag.embedder import embed_texts

console = Console()

DOCUMENTS_DIR = Path(__file__).parent.parent / "src" / "rag" / "documents"


def load_markdown_files() -> list[dict]:
    """Baca semua file .md dan ekstrak metadata dari nama file dan konten."""
    docs = []
    for md_file in sorted(DOCUMENTS_DIR.glob("*.md")):
        content = md_file.read_text(encoding="utf-8").strip()

        # Ekstrak judul dari baris pertama (## atau #)
        title = md_file.stem
        for line in content.splitlines():
            if line.startswith("#"):
                title = line.lstrip("#").strip()
                break

        # Ekstrak kategori dan severity dari konten
        category, severity = "", ""
        for line in content.splitlines():
            if line.startswith("## Kategori"):
                pass
            elif category == "" and "## Kategori" in content:
                idx = content.find("## Kategori")
                after = content[idx:].splitlines()
                if len(after) > 1:
                    category = after[1].strip()
            if line.startswith("## Severity"):
                pass
            elif severity == "" and "## Severity" in content:
                idx = content.find("## Severity")
                after = content[idx:].splitlines()
                if len(after) > 1:
                    severity = after[1].strip()

        docs.append({
            "content": content,
            "filename": md_file.name,
            "metadata": {
                "source": md_file.name,
                "title": title,
                "category": category,
                "severity": severity,
            }
        })
    return docs


async def get_existing_filenames(session) -> set[str]:
    """Ambil nama file yang sudah ada di DB untuk menghindari duplikasi."""
    result = await session.execute(
        text("SELECT doc_metadata->>'source' FROM documents")
    )
    return {row[0] for row in result.fetchall() if row[0]}


async def ingest(docs: list[dict]):
    async with AsyncSessionLocal() as session:
        existing = await get_existing_filenames(session)

        new_docs = [d for d in docs if d["filename"] not in existing]

        if not new_docs:
            console.print("[yellow]Semua dokumen sudah ada di database. Tidak ada yang diingest.[/yellow]")
            return 0

        console.print(f"[cyan]Mengembedding {len(new_docs)} dokumen baru...[/cyan]")
        texts = [d["content"] for d in new_docs]
        embeddings = embed_texts(texts)

        for doc_data, embedding in zip(new_docs, embeddings):
            doc = Document(
                content=doc_data["content"],
                embedding=embedding,
                doc_metadata=doc_data["metadata"],
            )
            session.add(doc)

        await session.commit()
        return len(new_docs)


async def main():
    console.print("\n[bold cyan]═══ Phase 2 — RAG Knowledge Base Ingest ═══[/bold cyan]\n")

    # 1. Load dokumen dari file
    docs = load_markdown_files()
    console.print(f"[green]✅ Ditemukan {len(docs)} file dokumen di src/rag/documents/[/green]")
    for d in docs:
        console.print(f"   [dim]• {d['filename']} — {d['metadata']['title']}[/dim]")

    console.print()

    # 2. Ingest ke database
    console.print("[cyan]Memuat embedding model (pertama kali butuh download ~90MB)...[/cyan]")
    count = await ingest(docs)

    if count > 0:
        console.print(f"\n[bold green]✅ {count} dokumen berhasil diingest ke tabel documents![/bold green]")
    console.print("[dim]Jalankan: python scripts/verify_rag.py[/dim]\n")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
