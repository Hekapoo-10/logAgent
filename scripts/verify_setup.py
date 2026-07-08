"""
Verification script for Phase 0.
Run after Docker is up and .env is filled.
"""
import sys
import os
import asyncio

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rich.console import Console
from rich.table import Table

console = Console()


def check_env_file():
    from dotenv import load_dotenv
    load_dotenv()

    required_vars = [
        "DATABASE_URL",
        "OPENROUTER_API_KEY",
        "TELEGRAM_BOT_TOKEN",
        "EMBEDDING_MODEL",
    ]
    missing = [v for v in required_vars if not os.getenv(v)]
    if missing:
        return False, f"Missing variables: {', '.join(missing)}"
    return True, "All required env vars present"


async def check_postgres():
    import asyncpg
    from dotenv import load_dotenv
    load_dotenv()

    url = os.getenv("DATABASE_URL", "").replace("postgresql+asyncpg://", "")
    try:
        # asyncpg uses different URL format
        db_url = os.getenv("DATABASE_URL", "").replace(
            "postgresql+asyncpg://", "postgresql://"
        )
        conn = await asyncpg.connect(db_url, timeout=5)
        version = await conn.fetchval("SELECT version()")
        await conn.close()
        return True, f"Connected — {version[:40]}..."
    except Exception as e:
        return False, str(e)


async def check_pgvector():
    import asyncpg
    from dotenv import load_dotenv
    load_dotenv()

    try:
        db_url = os.getenv("DATABASE_URL", "").replace(
            "postgresql+asyncpg://", "postgresql://"
        )
        conn = await asyncpg.connect(db_url, timeout=5)
        result = await conn.fetchval(
            "SELECT COUNT(*) FROM pg_available_extensions WHERE name = 'vector'"
        )
        await conn.close()
        if result and result > 0:
            return True, "pgvector extension available"
        return False, "pgvector extension NOT found in this PostgreSQL"
    except Exception as e:
        return False, str(e)


def check_imports():
    packages = [
        ("fastapi", "FastAPI"),
        ("sqlalchemy", "SQLAlchemy"),
        ("asyncpg", "asyncpg"),
        ("pgvector", "pgvector"),
        ("langchain", "LangChain"),
        ("sentence_transformers", "sentence-transformers"),
        ("openai", "openai"),
        ("telegram", "python-telegram-bot"),
        ("dotenv", "python-dotenv"),
        ("rich", "rich"),
    ]
    failed = []
    for module, name in packages:
        try:
            __import__(module)
        except ImportError:
            failed.append(name)
    if failed:
        return False, f"Missing packages: {', '.join(failed)}"
    return True, "All packages importable"


async def main():
    console.print("\n[bold cyan]═══ Phase 0 Verification ═══[/bold cyan]\n")

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Check", style="cyan", width=30)
    table.add_column("Status", width=10)
    table.add_column("Detail", width=50)

    checks = []

    # 1. Env file
    ok, msg = check_env_file()
    checks.append((".env variables", ok, msg))

    # 2. Package imports
    ok, msg = check_imports()
    checks.append(("Python packages", ok, msg))

    # 3. PostgreSQL connection
    ok, msg = await check_postgres()
    checks.append(("PostgreSQL connection", ok, msg))

    # 4. pgvector availability
    if checks[-1][1]:  # only check if postgres connected
        ok, msg = await check_pgvector()
        checks.append(("pgvector extension", ok, msg))
    else:
        checks.append(("pgvector extension", False, "Skipped (no DB connection)"))

    all_passed = True
    for name, ok, msg in checks:
        status = "[green]✅ PASS[/green]" if ok else "[red]❌ FAIL[/red]"
        table.add_row(name, status, msg)
        if not ok:
            all_passed = False

    console.print(table)

    if all_passed:
        console.print("\n[bold green]✅ Phase 0 COMPLETE — Lanjut ke Phase 1![/bold green]\n")
    else:
        console.print("\n[bold red]❌ Ada yang perlu diperbaiki sebelum lanjut.[/bold red]")
        console.print("[yellow]Lihat detail error di atas dan ikuti instruksi di PROGRESS.md[/yellow]\n")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
