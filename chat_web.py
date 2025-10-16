from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
import os, json, glob
from openai import OpenAI

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

DATA_DIR = "/data"
SNIPPETS = glob.glob(os.path.join(DATA_DIR, "snippets/*.jsonl"))

def load_context(max_lines=30):
    ctx = []
    for p in SNIPPETS:
        try:
            with open(p, "r", encoding="utf-8") as f:
                for i, line in enumerate(f):
                    if i >= max_lines: break
                    try:
                        obj = json.loads(line)
                        txt = obj.get("text") or obj.get("content") or ""
                        if txt: ctx.append(txt.strip())
                    except:
                        continue
        except:
            continue
    return ctx

def build_prompt(q: str):
    ctx = load_context()
    ctx_text = "\n- ".join(ctx[:20]) if ctx else "لا توجد معرفة متاحة بعد."
    return (
        "أنت مساعد عربي دقيق ومختصر. استخدم السياق التالي إن كان مفيدًا.\n\n"
        f"السياق:\n- {ctx_text}\n\n"
        f"السؤال: {q}\n"
        "الإجابة:"
    )

app = FastAPI(title="AutoLearn Chat")

@app.get("/", response_class=HTMLResponse)
def index():
    return """
<!doctype html><meta charset='utf-8'><title>AutoLearn Chat</title>
<style>
body{background:#0b1220;color:#e7ecff;font-family:system-ui;margin:0}
.wrap{max-width:820px;margin:40px auto;padding:0 16px}
.card{background:#0f1a2b;border:1px solid #1e2b44;border-radius:16px;padding:16px}
.row{display:flex;gap:8px;margin:8px 0}
input{flex:1;padding:12px 14px;border:1px solid #1e2b44;border-radius:12px;background:#0c1626;color:#e7ecff}
button{padding:12px 16px;border:1px solid #1e2b44;border-radius:12px;background:#1a2742;color:#e7ecff;cursor:pointer}
pre{white-space:pre-wrap;background:#0b162a;border:1px solid #1e2b44;border-radius:12px;padding:12px;min-height:80px}
</style>
<div class="wrap">
  <h1>💬 محادثة AutoLearn</h1>
  <div class="card">
    <div class="row">
      <input id="q" placeholder="اكتب سؤالك هنا..." />
      <button id="ask">اسأل</button>
    </div>
    <pre id="ans"></pre>
  </div>
  <p>ملاحظة: إن كانت قاعدة المعرفة فارغة، سيُجاب من النموذج مباشرة.</p>
</div>
<script>
const q   = document.getElementById('q');
const ask = document.getElementById('ask');
const ans = document.getElementById('ans');
async function askFn(){
  const qq = (q.value||'').trim();
  if(!qq){ ans.textContent='اكتب سؤالاً أولاً.'; return; }
  ans.textContent='...جارِ توليد الإجابة';
  try{
    const r = await fetch('/ask', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({q:qq})});
    const j = await r.json();
    ans.textContent = j.answer || j.detail || 'لم يتم الحصول على إجابة.';
  }catch(e){ ans.textContent = 'خطأ في الاتصال: '+e; }
}
ask.onclick = askFn;
q.addEventListener('keydown', e => { if(e.key==='Enter') askFn(); });
</script>
"""

@app.post("/ask")
async def ask(request: Request):
    data = await request.json()
    q = (data.get("q") or "").strip()
    if not q:
        return JSONResponse({"answer":"الرجاء كتابة سؤال."}, status_code=400)
    if not client:
        return JSONResponse({"answer":"لم يتم إعداد OPENAI_API_KEY في Render."}, status_code=200)

    prompt = build_prompt(q)
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role":"user","content":prompt}],
            temperature=0.2,
        )
        return {"answer": resp.choices[0].message.content.strip()}
    except Exception as e:
        return JSONResponse({"answer": f"تعذّر التوليد: {e}"}, status_code=200)
