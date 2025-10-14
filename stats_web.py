# stats_web.py
import os, sqlite3
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

DB_PATH = os.getenv("AUTOLEARN_DB", "/data/autolearn.db")
app = FastAPI(title="AutoLearn Dashboard")

def read_stats():
    stats = {"db_exists": os.path.exists(DB_PATH), "size_mb": 0, "docs": 0, "chunks": 0, "insights": 0}
    if not stats["db_exists"]:
        return stats
    try:
        stats["size_mb"] = round(os.path.getsize(DB_PATH) / (1024 * 1024), 2)
        con = sqlite3.connect(DB_PATH)
        cur = con.cursor()
        for t in ("docs", "chunks", "insights"):
            try:
                stats[t] = cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            except Exception:
                stats[t] = 0
        con.close()
    except Exception:
        pass
    return stats

@app.get("/", response_class=HTMLResponse)
def home():
    s = read_stats()
    return f"""
    <html><body style="font-family:system-ui;margin:40px">
      <h1>لوحة AutoLearn</h1>
      <p>تحدّث كل 60 ثانية تلقائيًا.</p>
      <ul>
        <li>حالة القاعدة: {"موجودة" if s['db_exists'] else "غير موجودة"}</li>
        <li>الحجم (MB): {s['size_mb']}</li>
        <li>عدد المستندات: {s['docs']}</li>
        <li>عدد المقاطع: {s['chunks']}</li>
        <li>عدد المعارف: {s['insights']}</li>
      </ul>
      <script>setTimeout(()=>location.reload(),60000)</script>
    </body></html>
    """

@app.get("/stats.json")
def stats_json():
    return JSONResponse(read_stats())
