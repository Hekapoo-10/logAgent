"""
FastAPI application entry point.
Jalankan dengan: uvicorn src.api.main:app --reload
"""
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.routes import alerts, analyze, predict
from src.database.connection import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: jalankan Telegram bot polling di background. Shutdown: cleanup."""
    import asyncio
    from src.bot.telegram import start_bot

    bot_task = asyncio.create_task(start_bot())
    print("✅ BGL Log Anomaly API started.")
    yield
    bot_task.cancel()
    await engine.dispose()
    print("🔴 BGL Log Anomaly API stopped.")


app = FastAPI(
    title="BGL Log Anomaly Monitoring API",
    description=(
        "REST API untuk sistem monitoring anomali log supercomputer BGL. "
        "Pipeline: LogBERT output → Retrieval Agent → Document Agent → Telegram Alert."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ─── Middleware ────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log setiap request masuk beserta response time-nya."""
    start = time.monotonic()
    response = await call_next(request)
    elapsed = round((time.monotonic() - start) * 1000, 2)
    print(f"[{request.method}] {request.url.path} → {response.status_code} ({elapsed}ms)")
    return response


# ─── Global Error Handler ──────────────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": type(exc).__name__,
            "detail": str(exc),
        },
    )


# ─── Routes ───────────────────────────────────────────────────────────────────

app.include_router(predict.router)
app.include_router(alerts.router)
app.include_router(analyze.router)
