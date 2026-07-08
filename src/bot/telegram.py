"""
Telegram Bot — Delivery channel untuk alert anomali BGL.

Dua mode operasi:
1. PUSH (otomatis): send_alert() dipanggil FastAPI saat anomali terdeteksi
2. PULL (on-demand): user ketik command ke bot (/start, /status, /history, /help)

Bot berjalan sebagai background task di dalam FastAPI lifespan.
"""
import logging
from datetime import datetime, timezone

import httpx
from sqlalchemy import select, func
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from src.config.settings import settings
from src.database.connection import AsyncSessionLocal
from src.database.models import AlertHistory

logger = logging.getLogger(__name__)

TELEGRAM_API = f"https://api.telegram.org/bot{settings.telegram_bot_token}"

SEVERITY_EMOJI = {
    "CRITICAL": "🔴",
    "HIGH":     "🟠",
    "MEDIUM":   "🟡",
    "LOW":      "🟢",
}


# ─── Push Alert (dipanggil FastAPI) ───────────────────────────────────────────

def _format_alert(alert_doc, req) -> str:
    """Format dokumen alert menjadi pesan Telegram (HTML)."""
    severity = getattr(alert_doc, "severity", "HIGH").upper()
    emoji = SEVERITY_EMOJI.get(severity, "🟠")

    log_keys_str = ", ".join(req.log_keys[:5]) if req.log_keys else "—"
    if len(req.log_keys) > 5:
        log_keys_str += f" (+{len(req.log_keys) - 5} lainnya)"

    return (
        f"{emoji} <b>ANOMALI TERDETEKSI — {severity}</b>\n"
        f"{'─' * 35}\n"
        f"📊 <b>Anomaly Score:</b> {req.anomaly_score:.4f}\n"
        f"🪟 <b>Window ID:</b> <code>{req.window_id}</code>\n"
        f"🔑 <b>Log Keys:</b> <code>{log_keys_str}</code>\n\n"
        f"📋 <b>{alert_doc.title}</b>\n\n"
        f"📝 <b>Ringkasan:</b>\n{alert_doc.summary}\n\n"
        f"🔍 <b>Konteks:</b>\n{alert_doc.context}\n\n"
        f"✅ <b>Rekomendasi:</b>\n{alert_doc.recommendation}\n"
        f"{'─' * 35}\n"
        f"⏰ {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC"
    )


async def send_alert(alert_doc, req) -> None:
    """
    Push alert ke Telegram chat.
    Dipanggil oleh FastAPI route POST /predict setelah Document Agent selesai.
    """
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        raise ValueError("TELEGRAM_BOT_TOKEN atau TELEGRAM_CHAT_ID belum diisi di .env")

    message = _format_alert(alert_doc, req)

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            f"{TELEGRAM_API}/sendMessage",
            json={
                "chat_id": settings.telegram_chat_id,
                "text": message,
                "parse_mode": "HTML",
            },
        )
        response.raise_for_status()


# ─── Bot Command Handlers ──────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "👋 <b>BGL Log Anomaly Monitor</b>\n\n"
        "Saya akan mengirim alert otomatis setiap kali anomali terdeteksi "
        "pada supercomputer BGL.\n\n"
        "Gunakan perintah berikut:\n"
        "/status — Status sistem saat ini\n"
        "/history — 5 alert anomali terakhir\n"
        "/help — Bantuan",
        parse_mode="HTML",
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "📖 <b>Daftar Perintah</b>\n\n"
        "/start — Perkenalan bot\n"
        "/status — Cek status sistem & statistik hari ini\n"
        "/history — Tampilkan 5 alert terakhir\n"
        "/help — Tampilkan pesan ini",
        parse_mode="HTML",
    )


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Tampilkan statistik anomali hari ini."""
    try:
        async with AsyncSessionLocal() as db:
            # Total anomali hari ini
            today = datetime.now(timezone.utc).date()
            result = await db.execute(
                select(func.count())
                .select_from(AlertHistory)
                .where(
                    AlertHistory.is_anomaly == True,
                    func.date(AlertHistory.created_at) == today,
                )
            )
            today_count = result.scalar() or 0

            # Total keseluruhan
            result = await db.execute(
                select(func.count()).select_from(AlertHistory)
                .where(AlertHistory.is_anomaly == True)
            )
            total_count = result.scalar() or 0

            # Rata-rata anomaly score
            result = await db.execute(
                select(func.avg(AlertHistory.anomaly_score))
                .where(AlertHistory.is_anomaly == True)
            )
            avg_score = result.scalar()

        await update.message.reply_text(
            "📊 <b>Status Sistem</b>\n\n"
            f"🟢 API: Online\n"
            f"📅 Anomali hari ini: <b>{today_count}</b>\n"
            f"📦 Total anomali: <b>{total_count}</b>\n"
            f"📈 Rata-rata score: <b>{avg_score:.4f}</b>\n\n"
            f"⏰ {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC",
            parse_mode="HTML",
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Error mengambil status: {e}")


async def cmd_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Tampilkan 5 alert anomali terakhir."""
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(AlertHistory)
                .where(AlertHistory.is_anomaly == True)
                .order_by(AlertHistory.created_at.desc())
                .limit(5)
            )
            records = result.scalars().all()

        if not records:
            await update.message.reply_text("📭 Belum ada alert anomali yang tercatat.")
            return

        lines = ["📜 <b>5 Alert Terakhir</b>\n"]
        for i, r in enumerate(records, 1):
            severity = "—"
            # Coba ekstrak severity dari alert_title jika ada
            emoji = "🟠"
            ts = r.created_at.strftime("%m-%d %H:%M") if r.created_at else "—"
            title = r.alert_title or "Anomali tidak bernama"
            lines.append(
                f"{i}. {emoji} <b>{title[:45]}</b>\n"
                f"   Score: {r.anomaly_score:.3f} | {ts} UTC\n"
                f"   Telegram: {r.telegram_status}\n"
            )

        await update.message.reply_text("\n".join(lines), parse_mode="HTML")

    except Exception as e:
        await update.message.reply_text(f"❌ Error mengambil history: {e}")


# ─── Background Bot Runner ─────────────────────────────────────────────────────

def build_application() -> Application:
    """Buat instance bot dengan semua command handler terdaftar."""
    app = (
        Application.builder()
        .token(settings.telegram_bot_token)
        .build()
    )
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("history", cmd_history))
    return app


async def start_bot() -> None:
    """
    Jalankan bot dalam mode polling sebagai background task.
    Dipanggil dari FastAPI lifespan di main.py.
    """
    if not settings.telegram_bot_token:
        logger.warning("TELEGRAM_BOT_TOKEN tidak diisi — bot tidak dijalankan.")
        return

    bot_app = build_application()
    await bot_app.initialize()
    await bot_app.start()
    await bot_app.updater.start_polling(drop_pending_updates=True)
    logger.info("✅ Telegram bot polling started.")
