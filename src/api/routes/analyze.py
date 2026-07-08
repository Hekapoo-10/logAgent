"""
UI demo sederhana + endpoint /analyze.

Alur: user menempel baris log mentah di halaman web → POST /analyze →
model asli (LogBERT+DeepSVDD) menghitung skor → jika anomali, full pipeline
(Retrieval → Document → Telegram) dijalankan → hasil ditampilkan di halaman.

Endpoint ini untuk DEMO/uji manual. Integrasi produksi tetap lewat POST /predict.
"""
from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.routes.predict import predict as run_pipeline
from src.api.schemas import PredictRequest
from src.database.connection import get_db

router = APIRouter(tags=["UI Demo"])


class AnalyzeRequest(BaseModel):
    log_text: str


@router.post("/analyze")
async def analyze(body: AnalyzeRequest, db: AsyncSession = Depends(get_db)):
    """Terima log mentah, jalankan model + full pipeline, kembalikan hasil."""
    # Import di dalam fungsi supaya torch/BERT hanya dimuat saat pertama dipakai
    from src.model.predict import predict as model_predict

    lines = [ln for ln in body.log_text.splitlines() if ln.strip()]
    if not lines:
        return {"success": False, "error": "Log kosong", "detail": "Masukkan minimal 1 baris log."}

    out = model_predict(lines)
    req = PredictRequest(
        anomaly_score=out["anomaly_score"],
        is_anomaly=out["is_anomaly"],
        log_keys=out["log_keys"],
        log_sequence=lines,
        window_id=out["window_id"],
        timestamp=out["timestamp"],
    )
    return await run_pipeline(req, db)


@router.get("/", response_class=HTMLResponse)
async def ui():
    return HTML_PAGE


HTML_PAGE = """<!doctype html>
<html lang="id">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>BGL Log Anomaly Monitor</title>
<style>
  :root { color-scheme: light dark; }
  * { box-sizing: border-box; }
  body {
    font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
    max-width: 760px; margin: 0 auto; padding: 24px;
    background: #0f1116; color: #e6e6e6;
  }
  @media (prefers-color-scheme: light) {
    body { background: #f5f6f8; color: #1a1a1a; }
    .card { background: #fff !important; border-color: #e0e0e0 !important; }
    textarea { background: #fff !important; color: #1a1a1a !important; border-color: #ccc !important; }
  }
  h1 { font-size: 1.4rem; margin: 0 0 4px; }
  .sub { color: #8a8f98; font-size: .85rem; margin-bottom: 20px; }
  textarea {
    width: 100%; height: 200px; padding: 12px; border-radius: 8px;
    border: 1px solid #2a2e37; background: #171a21; color: #e6e6e6;
    font-family: ui-monospace, Menlo, Consolas, monospace; font-size: .8rem; resize: vertical;
  }
  .row { display: flex; gap: 10px; margin-top: 12px; flex-wrap: wrap; }
  button {
    padding: 10px 18px; border: none; border-radius: 8px; cursor: pointer;
    font-size: .9rem; font-weight: 600;
  }
  .primary { background: #3b82f6; color: #fff; }
  .primary:disabled { opacity: .5; cursor: not-allowed; }
  .ghost { background: transparent; border: 1px solid #3a3f4a; color: #9aa0aa; }
  .card {
    margin-top: 20px; padding: 18px; border-radius: 10px;
    background: #171a21; border: 1px solid #2a2e37;
  }
  .badge { display: inline-block; padding: 3px 10px; border-radius: 999px; font-size: .8rem; font-weight: 700; }
  .anom { background: #7f1d1d; color: #fecaca; }
  .norm { background: #14532d; color: #bbf7d0; }
  .sev { float: right; padding: 3px 10px; border-radius: 6px; font-size: .75rem; font-weight: 700; }
  .CRITICAL { background:#7f1d1d; color:#fecaca; } .HIGH { background:#7c2d12; color:#fed7aa; }
  .MEDIUM { background:#713f12; color:#fde68a; } .LOW { background:#14532d; color:#bbf7d0; }
  .k { color: #8a8f98; font-size: .8rem; }
  .v { font-weight: 600; }
  h3 { margin: 14px 0 6px; font-size: 1rem; }
  p.body { margin: 4px 0; line-height: 1.5; white-space: pre-wrap; font-size: .9rem; }
  .tg { margin-top: 12px; font-size: .85rem; }
  .spin { display:inline-block; width:14px; height:14px; border:2px solid #fff; border-top-color:transparent;
          border-radius:50%; animation: s .7s linear infinite; vertical-align:-2px; }
  @keyframes s { to { transform: rotate(360deg); } }
  h2 { font-size: 1.1rem; margin: 28px 0 0; }
  .muted { color: #8a8f98; font-size: .8rem; }
  table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: .82rem; }
  th, td { text-align: left; padding: 7px 8px; border-bottom: 1px solid #2a2e37; }
  th { color: #8a8f98; font-weight: 600; }
  .pill { padding: 2px 8px; border-radius: 999px; font-size: .72rem; font-weight: 700; }
  .sent { background:#14532d; color:#bbf7d0; } .failed { background:#7f1d1d; color:#fecaca; }
  .skipped { background:#374151; color:#cbd5e1; } .pending { background:#713f12; color:#fde68a; }
</style>
</head>
<body>
  <h1>🖥️ BGL Log Anomaly Monitor</h1>
  <div class="sub">Tempel baris log BGL → sistem mendeteksi anomali & mengirim alert ke Telegram.</div>

  <textarea id="log" placeholder="Tempel baris log BGL di sini, satu baris per log..."></textarea>
  <div class="row">
    <button class="primary" id="go" onclick="analyze()">Analisis &amp; Kirim ke Telegram</button>
    <button class="ghost" onclick="fillSample()">Isi contoh anomali</button>
  </div>

  <div id="result"></div>

  <h2>📊 Riwayat Alert <span class="muted">(live — refresh tiap 5 detik)</span></h2>
  <table id="feed">
    <thead><tr><th>Waktu</th><th>Window</th><th>Score</th><th>Judul</th><th>Telegram</th></tr></thead>
    <tbody><tr><td colspan="5" class="muted">Memuat...</td></tr></tbody>
  </table>

<script>
const SAMPLE = `KERNMC 1117869872 2005.06.04 R23-M1-N0 2005-06-04 R23-M1-N0 RAS KERNEL FATAL ciod: failed to read message prefix on control stream
KERNMC 1117869873 2005.06.04 R23-M1-N0 2005-06-04 R23-M1-N0 RAS KERNEL FATAL ciod: Error reading message prefix after LOGIN_MESSAGE
APPREAD 1117869874 2005.06.04 R23-M1-N4 2005-06-04 R23-M1-N4 RAS KERNEL FATAL ciod: failed to read message prefix on control stream
KERNMC 1117869875 2005.06.04 R23-M1-N0 2005-06-04 R23-M1-N0 RAS KERNEL FATAL data storage interrupt
KERNDTLB 1117869876 2005.06.04 R23-M1-N0 2005-06-04 R23-M1-N0 RAS KERNEL FATAL data TLB error interrupt
KERNMC 1117869877 2005.06.04 R23-M1-N0 2005-06-04 R23-M1-N0 RAS KERNEL FATAL machine check interrupt
KERNRTSP 1117869878 2005.06.04 R23-M1-N0 2005-06-04 R23-M1-N0 RAS KERNEL FATAL rts panic! - stopping execution`;

function fillSample(){ document.getElementById('log').value = SAMPLE; }

async function analyze(){
  const log = document.getElementById('log').value.trim();
  const res = document.getElementById('result');
  const btn = document.getElementById('go');
  if(!log){ res.innerHTML = '<div class="card">Masukkan log dulu.</div>'; return; }
  btn.disabled = true;
  res.innerHTML = '<div class="card"><span class="spin"></span> Memproses (model + retrieval + LLM)... butuh beberapa detik.</div>';
  try {
    const r = await fetch('/analyze', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({log_text: log})
    });
    const j = await r.json();
    render(j);
    loadFeed();
  } catch(e){
    res.innerHTML = '<div class="card">❌ Error: '+e+'</div>';
  } finally { btn.disabled = false; }
}

async function loadFeed(){
  try {
    const r = await fetch('/alerts?limit=15');
    const j = await r.json();
    const tb = document.querySelector('#feed tbody');
    if(!j.success || !j.data.items.length){
      tb.innerHTML = '<tr><td colspan="5" class="muted">Belum ada data.</td></tr>'; return;
    }
    tb.innerHTML = j.data.items.map(function(it){
      const t = it.created_at ? new Date(it.created_at).toLocaleTimeString() : '-';
      const st = it.telegram_status || '-';
      const sc = (it.anomaly_score!=null) ? it.anomaly_score.toFixed(3) : '';
      const title = it.alert_title || (it.is_anomaly ? '' : '— normal —');
      const cls = it.is_anomaly ? '' : ' class="muted"';
      return '<tr'+cls+'><td>'+t+'</td><td>'+(it.window_id||'')+'</td><td>'+sc
        +'</td><td>'+title+'</td><td><span class="pill '+st+'">'+st+'</span></td></tr>';
    }).join('');
  } catch(e){}
}
loadFeed();
setInterval(loadFeed, 5000);

function render(j){
  const res = document.getElementById('result');
  if(!j.success){ res.innerHTML = '<div class="card">❌ '+(j.detail||j.error||'Gagal')+'</div>'; return; }
  const d = j.data;
  if(!d.is_anomaly){
    res.innerHTML = '<div class="card"><span class="badge norm">NORMAL</span> '
      + '<span class="v">Score '+d.anomaly_score+'</span><br><br>'
      + 'Tidak terdeteksi anomali — tidak ada alert dikirim.</div>';
    return;
  }
  const sev = (d.severity||'HIGH').toUpperCase();
  res.innerHTML = '<div class="card">'
    + '<span class="badge anom">ANOMALI</span> '
    + '<span class="v">Score '+d.anomaly_score+'</span>'
    + '<span class="sev '+sev+'">'+sev+'</span>'
    + '<h3>'+ (d.alert_title||'') +'</h3>'
    + '<p class="body">'+ (d.alert_summary||'') +'</p>'
    + '<h3>Konteks</h3><p class="body">'+ (d.alert_context||'') +'</p>'
    + '<h3>Rekomendasi</h3><p class="body">'+ (d.alert_recommendation||'') +'</p>'
    + '<div class="tg">📲 Telegram: <span class="v">'+ (d.telegram_status||'-') +'</span> '
    + '&nbsp;|&nbsp; 🪟 '+ (d.window_id||'') +'</div>'
    + '</div>';
}
</script>
</body>
</html>"""
