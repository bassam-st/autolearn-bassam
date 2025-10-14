import os, sqlite3, time
from typing import List, Tuple
from duckduckgo_search import DDGS
from readability import Document
from bs4 import BeautifulSoup
import requests
import numpy as np

USE_OPENAI = bool(os.getenv("OPENAI_API_KEY"))
USE_GEMINI = bool(os.getenv("GEMINI_API_KEY"))
DB_PATH = os.getenv("AUTOLEARN_DB", "autolearn.db")

from sentence_transformers import SentenceTransformer
_embedder = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

def _emb(text: str) -> np.ndarray:
    v = _embedder.encode([text], normalize_embeddings=True)[0]
    return v.astype(np.float32)

def _fetch_url(url: str, limit=120000) -> str:
    try:
        r = requests.get(url, timeout=12, headers={"User-Agent":"Mozilla/5.0"})
        r.raise_for_status()
        html = r.text[:limit]
        doc = Document(html)
        txt = BeautifulSoup(doc.summary(), "lxml").get_text(" ", strip=True)
        return txt
    except Exception:
        return ""

def _search_web(q: str, k=5) -> List[Tuple[str,str]]:
    res = []
    with DDGS() as ddgs:
        for r in ddgs.text(q, max_results=k, safesearch="moderate", region="wt-wt"):
            u = r.get("href") or r.get("url")
            t = r.get("title","")
            if u: res.append((t, u))
    return res

def _topk_memory(q: str, k=6) -> List[Tuple[str,str]]:
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    try:
        cur.execute("SELECT doc_id, text FROM chunks LIMIT 2000")
        rows = cur.fetchall()
    except Exception:
        rows = []
    con.close()
    if not rows: return []
    qv = _emb(q)
    scored = []
    for doc_id, text in rows:
        tv = _emb(text[:512])
        sim = float(np.dot(qv, tv))
        scored.append((sim, doc_id, text))
    scored.sort(reverse=True, key=lambda x: x[0])
    return [(doc_id, text) for _, doc_id, text in scored[:k]]

def _llm_answer(prompt: str) -> str:
    if USE_OPENAI:
        from openai import OpenAI
        cl = OpenAI()
        r = cl.chat.completions.create(
            model=os.getenv("OPENAI_MODEL","gpt-4o-mini"),
            messages=[{"role":"system","content":"أجب بالعربية بدقة وباختصار ثم تفاصيل مع مصادر."},
                      {"role":"user","content":prompt}],
            temperature=0.2, max_tokens=800)
        return r.choices[0].message.content.strip()
    if USE_GEMINI:
        import google.generativeai as genai
        genai.configure(api_key=os.environ["GEMINI_API_KEY"])
        m = genai.GenerativeModel(os.getenv("GEMINI_MODEL","gemini-1.5-pro"))
        r = m.generate_content(prompt)
        return r.text or ""
    return "ملخص أولي (LLM غير مفعّل):\n" + prompt[:600]

def answer_question(question: str) -> dict:
    t0 = time.time()
    mem_hits = _topk_memory(question, k=6)
    web_hits = _search_web(question, k=5)
    web_texts = []
    for title, url in web_hits[:3]:
        txt = _fetch_url(url)
        if txt:
            web_texts.append((title, url, txt[:2000]))

    ctx = []
    if mem_hits:
        ctx.append("## مقتطفات من الذاكرة:\n" + "\n\n".join(t[:400] for _, t in mem_hits))
    if web_texts:
        ctx.append("## أحدث ما وُجد على الويب:\n" +
                   "\n\n".join(f"{t}\n{u}\n{tx[:400]}" for t,u,tx in web_texts))

    prompt = f"""سؤال: {question}

المعايير:
- ابدأ بخلاصة دقيقة، ثم نقاط تفصيلية.
- اذكر المصدر/التاريخ إن وُجد.
- لا تقدم تشخيصًا طبيًا مخصصًا.

السياق:
{'\n\n'.join(ctx) if ctx else 'لا سياق كافٍ'}

النتيجة: إجابة واضحة + نقاط + مصادر روابط إن توفرت.
"""
    answer = _llm_answer(prompt)
    return {
        "answer": answer,
        "sources": [u for _,u,_ in web_texts],
        "latency": round(time.time()-t0, 2),
        "used_llm": USE_OPENAI or USE_GEMINI
    }
