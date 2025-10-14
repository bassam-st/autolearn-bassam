# -*- coding: utf-8 -*-
import os, sqlite3, json, datetime as dt
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

DB = os.getenv("AUTOLEARN_DB", "autolearn.db")
app = FastAPI(title="AutoLearn Dashboard", version="1.0")

def _stats():
    if not os.path.exists(DB):
        return {"db_exists": False, "size_mb": 0, "docs": 0, "chunks": 0, "insights": 0}
    size_mb = os.path.getsize(DB) / (1024*1024)
    con = sqlite3.connect(DB); cur = con.cursor()
    def cnt(t):
        try: return cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        except: return 0
    data = {"db_exists": True, "size_mb": round(size_mb, 3),
            "docs": cnt("docs"), "chunks": cnt("chunks"), "insights": cnt("insights"),
            "updated_at": dt.datetime.utcnow().isoformat()+"Z"}
    con.close()
    return data

@app.get("/metrics")
def metrics(): return JSONResponse(_stats())

@app.get("/", response_class=HTMLResponse)
def home():
    return f"""
<!doctype html><meta charset="utf-8">
<title>AutoLearn Dashboard</title>
<style>
body{{background:#0b1220;color:#e9edf5;font-family:system-ui,Segoe UI,Arial}}
.card{{background:#121a2b;padding:18px;margin:14px;border-radius:14px}}
h1{{margin:16px}} .k{{color:#8ab4ff}} .v{{color:#fff}}
.small{{opacity:.7;font-size:.9rem}}
</style>
<h1>لوحة AutoLearn</h1>
<div class="card" id="s">تحميل stats...</div>
<script>
async function load() {{
  const r = await fetch('/metrics'); const s = await r.json();
  let html = `<div class=small>يُحدّث تلقائيًا كل 60 ثانية</div>
  <div class=card>
  <div><span class=k>حالة القاعدة:</span> <span class=v>{'{'}{'}'} s.db_exists ? 'موجودة' : 'غير موجودة' {'{'}{'}'}</span></div>
  <div><span class=k>الحجم (MB):</span> <span class=v>{'{'}{'}'} s.size_mb {'{'}{'}'}</span></div>
  <div><span class=k>عدد المستندات:</span> <span class=v>{'{'}{'}'} s.docs {'{'}{'}'}</span></div>
  <div><span class=k>عدد المقاطع:</span> <span class=v>{'{'}{'}'} s.chunks {'{'}{'}'}</span></div>
  <div><span class=k>عدد المعارف:</span> <span class=v>{'{'}{'}'} s.insights {'{'}{'}'}</span></div>
  <div class=small>آخر تحديث: { '{' }{ '{' } s.updated_at { '}' }{ '}' }</div>
  </div>`;
  document.getElementById('s').innerHTML = html;
}}
load(); setInterval(load, 60000);
</script>
"""
