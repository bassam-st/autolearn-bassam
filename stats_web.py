from fastapi import FastAPI, Body
from fastapi.responses import JSONResponse, HTMLResponse
import os, sqlite3, math, time
from qa import answer_question

app = FastAPI(title="AutoLearn Dashboard")

DB_PATH = os.getenv("AUTOLEARN_DB", "autolearn.db")

@app.get("/")
def home():
    # نفس بطاقات الإحصاء الموجودة عندك (اختصرنا هنا)
    ok = os.path.exists(DB_PATH)
    size_mb = round(os.path.getsize(DB_PATH)/(1024*1024),2) if ok else 0.0
    con = sqlite3.connect(DB_PATH) if ok else None
    def _count(t):
        if not ok: return 0
        try:
            return con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        except: return 0
    docs = _count("docs"); chunks = _count("chunks"); ins = _count("insights")
    if con: con.close()
    return {"db_exists": ok, "db": DB_PATH, "size_mb": size_mb,
            "docs": docs, "chunks": chunks, "insights": ins, "updated": int(time.time())}

# ========= واجهة الأسئلة =========
@app.post("/ask")
def ask_api(payload: dict = Body(...)):
    q = (payload.get("q") or "").strip()
    if not q:
        return JSONResponse({"error":"سؤال فارغ"}, status_code=400)
    return answer_question(q)

@app.get("/chat", response_class=HTMLResponse)
def chat_page():
    return """
<!doctype html><meta charset="utf-8">
<title>AutoLearn Chat</title>
<style>body{font-family:sans-serif;background:#0a1020;color:#e8ecff;margin:20px}
#log{white-space:pre-wrap;border:1px solid #334;padding:12px;border-radius:12px;min-height:220px}
input,button{padding:10px;border-radius:10px;border:1px solid #334;background:#111a33;color:#fff}
a{color:#9cf}</style>
<h2>الدردشة مع AutoLearn</h2>
<div id="log">اكتب سؤالك…</div><br/>
<input id="q" placeholder="مثال: آخر أخبار الذكاء الاصطناعي" size="60"/>
<button onclick="ask()">إرسال</button>
<script>
async function ask(){
 const q = document.getElementById('q').value.trim();
 if(!q){return}
 document.getElementById('log').textContent="⏳ جاري البحث والتفكير…";
 const r = await fetch('/ask',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({q})});
 const j = await r.json();
 const src = (j.sources||[]).map(u=>`• <a href="${u}" target="_blank">${u}</a>`).join("<br/>");
 document.getElementById('log').innerHTML = (j.answer||"") + "<br/><br/><b>المصادر:</b><br/>" + src;
}
</script>
"""
