# ============================================
# 📊 AutoLearn Web Dashboard (stats_web.py)
# واجهة ويب خفيفة لعرض تطوّر قاعدة البيانات برسوم
# تتحدّث تلقائيًا كل 60 ثانية
# تشغيل:
#   pip install fastapi uvicorn
#   uvicorn stats_web:app --host 0.0.0.0 --port 8082
# افتح: http://localhost:8082
# ============================================

import os, sqlite3
from datetime import datetime
from fastapi import FastAPI
from fastapi.responses import JSONResponse, HTMLResponse

APP_PORT = int(os.getenv("STATS_PORT", "8082"))
DB_PATH = os.getenv("AUTOLEARN_DB", "autolearn.db")

app = FastAPI(title="AutoLearn Dashboard")

def read_metrics():
    exists = os.path.exists(DB_PATH)
    size_bytes = os.path.getsize(DB_PATH) if exists else 0
    size_mb = round(size_bytes / (1024 * 1024), 2)

    docs = chunks = insights = 0
    last_insight = None

    if exists:
        con = sqlite3.connect(DB_PATH, check_same_thread=False)
        cur = con.cursor()
        try:
            docs = cur.execute("SELECT COUNT(*) FROM docs").fetchone()[0]
        except Exception:
            docs = 0
        try:
            chunks = cur.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
        except Exception:
            chunks = 0
        try:
            insights = cur.execute("SELECT COUNT(*) FROM insights").fetchone()[0]
        except Exception:
            insights = 0
        try:
            last_insight = cur.execute("SELECT MAX(created_at) FROM insights").fetchone()[0]
        except Exception:
            last_insight = None
        con.close()

    return {
        "db_path": DB_PATH,
        "db_exists": exists,
        "db_size_mb": size_mb,
        "docs": docs,
        "chunks": chunks,
        "insights": insights,
        "last_insight_at": last_insight,
        "timestamp": datetime.utcnow().isoformat(timespec="seconds"),
    }

@app.get("/metrics")
def metrics():
    return JSONResponse(read_metrics())

@app.get("/")
def dashboard():
    html = f"""
<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<title>لوحة AutoLearn</title>
<link rel="preconnect" href="https://cdn.jsdelivr.net" />
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>
  :root {{ --bg:#0b1020; --card:#111936; --text:#e8eefc; --muted:#a9b4d0; --accent:#60a5fa; }}
  body {{ margin:0; font-family:system-ui,-apple-system,Segoe UI,Roboto; background:var(--bg); color:var(--text); }}
  .wrap {{ max-width:1100px; margin:32px auto; padding:0 16px; }}
  h1 {{ font-size:28px; margin:0 0 16px; }}
  .sub {{ color:var(--muted); margin-bottom:24px; }}
  .grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:16px; }}
  .card {{ background:var(--card); border-radius:16px; padding:16px; box-shadow:0 8px 24px rgba(0,0,0,.25); }}
  .kpi {{ font-size:28px; font-weight:700; }}
  .label {{ font-size:13px; color:var(--muted); margin-top:6px; }}
  .ok {{ color:#22c55e; }}
  .warn {{ color:#f59e0b; }}
  .bad {{ color:#ef4444; }}
  .muted {{ color:var(--muted); font-size:12px; }}
  canvas {{ background:#0c1430; border-radius:12px; padding:8px; }}
  footer {{ margin-top:24px; color:var(--muted); font-size:12px; text-align:center; }}
</style>
</head>
<body>
<div class="wrap">
  <h1>لوحة AutoLearn</h1>
  <div class="sub">مراقبة تطوّر قاعدة البيانات والتعلّم الذاتي — يتم التحديث تلقائيًا كل 60 ثانية.</div>

  <div class="grid">
    <div class="card">
      <div class="label">حالة القاعدة</div>
      <div id="db-state" class="kpi">—</div>
      <div class="muted" id="db-path">{DB_PATH}</div>
    </div>
    <div class="card">
      <div class="label">حجم قاعدة البيانات (MB)</div>
      <div id="db-size" class="kpi">0</div>
      <div class="muted">يزيد مع تراكم المعرفة</div>
    </div>
    <div class="card">
      <div class="label">عدد المستندات (docs)</div>
      <div id="docs" class="kpi">0</div>
    </div>
    <div class="card">
      <div class="label">عدد المقاطع (chunks)</div>
      <div id="chunks" class="kpi">0</div>
    </div>
    <div class="card">
      <div class="label">عدد المعارف (insights)</div>
      <div id="insights" class="kpi">0</div>
      <div class="muted" id="last-insight">—</div>
    </div>
  </div>

  <div class="card" style="margin-top:16px;">
    <div class="label">تطوّر المقاطع والمعارف مع الزمن</div>
    <canvas id="chart" height="120"></canvas>
  </div>

  <footer>© AutoLearn Dashboard — يتم التحديث كل 60 ثانية</footer>
</div>

<script>
const points = [];
const chunksSeries = [];
const insightsSeries = [];

const els = {{
  dbState: document.getElementById("db-state"),
  dbSize: document.getElementById("db-size"),
  docs: document.getElementById("docs"),
  chunks: document.getElementById("chunks"),
  insights: document.getElementById("insights"),
  last: document.getElementById("last-insight")
}};

const ctx = document.getElementById("chart").getContext("2d");
const chart = new Chart(ctx, {{
  type: "line",
  data: {{
    labels: points,
    datasets: [
      {{
        label: "chunks",
        data: chunksSeries,
        tension: 0.25
      }},
      {{
        label: "insights",
        data: insightsSeries,
        tension: 0.25
      }}
    ]
  }},
  options: {{
    responsive: true,
    plugins: {{
      legend: {{ labels: {{ color: "#e8eefc" }} }}
    }},
    scales: {{
      x: {{ ticks: {{ color: "#a9b4d0" }} }},
      y: {{ ticks: {{ color: "#a9b4d0" }} }}
    }}
  }}
}});

async function refresh() {{
  try {{
    const res = await fetch("/metrics");
    const m = await res.json();

    els.dbState.textContent = m.db_exists ? "متوفّرة ✅" : "غير موجودة ❌";
    els.dbState.className = "kpi " + (m.db_exists ? "ok" : "bad");
    els.dbSize.textContent = m.db_size_mb.toFixed(2);
    els.docs.textContent = m.docs;
    els.chunks.textContent = m.chunks;
    els.insights.textContent = m.insights;
    els.last.textContent = m.last_insight_at ? ("آخر Insight: " + m.last_insight_at) : "لم تُنشأ Insights بعد";

    const ts = new Date(m.timestamp);
    const label = ts.toLocaleTimeString([], {{hour: '2-digit', minute: '2-digit'}});
    points.push(label);
    chunksSeries.push(m.chunks);
    insightsSeries.push(m.insights);
    if (points.length > 60) {{ points.shift(); chunksSeries.shift(); insightsSeries.shift(); }}
    chart.update();
  }} catch (e) {{
    console.error(e);
  }}
}}

refresh();
setInterval(refresh, 60000); // 60s
</script>
</body>
</html>
"""
    return HTMLResponse(html)
