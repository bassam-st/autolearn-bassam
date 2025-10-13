import os, math, json, random, time
from typing import List, Dict, Optional
import numpy as np
from datetime import datetime
from sentence_transformers import SentenceTransformer
from schemas import SearchHit, Insight
from memory import Memory
from searcher import WebSearcher
from fetcher import fetch_and_extract

# اختياري: نمط مُعزَّز
USE_OPENAI = False
USE_GEMINI = False
try:
    if os.getenv("OPENAI_API_KEY"):
        from openai import OpenAI
        openai_client = OpenAI()
        USE_OPENAI = True
    if os.getenv("GEMINI_API_KEY"):
        import google.generativeai as genai
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        USE_GEMINI = True
except Exception:
    pass

class Learner:
    def __init__(self, cfg: Dict):
        self.cfg = cfg
        self.mem = Memory(cfg.get("db_path", "autolearn.db"))
        self.embed = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        self.searcher = WebSearcher(days=cfg.get("freshness_days", 365),
                                    blocked_domains=cfg.get("safety", {}).get("blocked_domains", []))
        self.min_chunk = cfg.get("min_chunk_len", 400)
        self.max_chunk = cfg.get("max_chunk_len", 2000)
        self.novelty_thr = cfg.get("novelty_threshold", 0.82)
        self.top_k = cfg.get("top_k_memory", 8)
        self.lang = cfg.get("language", "ar")

    # ---- تخطيط الاستعلامات ----
    def plan_queries(self, goal: str, prev_notes: List[str]) -> List[str]:
        seed = [
            f"{goal} best practices overview",
            f"{goal} pitfalls and limitations",
            f"{goal} evaluation and metrics",
            f"{goal} production case study",
            f"{goal} recent papers 2024 2025",
        ]
        if USE_OPENAI or USE_GEMINI:
            hints = self.llm_generate(f"اقترح 5 أسئلة/استعلامات مركّزة لجمع معرفة حول: {goal}")
            if hints:
                seed = [*seed[:2], *[h for h in hints[:5]]]
        random.shuffle(seed)
        return seed[: self.cfg.get("queries_per_cycle", 3)]

    # ---- جلب وفلترة النتائج ----
    def fetch_novel_docs(self, hits: List[SearchHit]) -> List[Dict]:
        kept = []
        for h in hits:
            try:
                page = fetch_and_extract(h.url, self.cfg.get("safety", {}).get("max_page_bytes", 2_000_000))
                text = page["text"]
                if len(text) < self.min_chunk:
                    continue
                doc_id = self.mem.upsert_doc(h.url, page["title"], text, page["published"], page["fetched_at"])
                # تقطيع النص إلى مقاطع
                chunks = self.chunk_text(text)
                for i, ch in enumerate(chunks):
                    vec = self.embed.encode(ch, normalize_embeddings=True)
                    # اختبار الجِدّة مقابل الذاكرة
                    sims = self.mem.top_similar(vec, topk=self.top_k)
                    is_novel = True
                    for _, _, s, _ in sims:
                        if s >= self.novelty_thr:
                            is_novel = False
                            break
                    if is_novel:
                        self.mem.add_chunk(doc_id, i, ch, vec.astype("float32"))
                        kept.append({"url": h.url, "title": page["title"], "chunk": ch})
            except Exception:
                continue
        return kept

    def chunk_text(self, text: str) -> List[str]:
        words = text.split()
        chunks, buf = [], []
        for w in words:
            buf.append(w)
            ln = sum(len(x) + 1 for x in buf)
            if ln >= self.max_chunk:
                chunks.append(" ".join(buf))
                buf = []
        if buf:
            ch = " ".join(buf)
            if len(ch) >= self.min_chunk:
                chunks.append(ch)
        return chunks

    # ---- توليد خلاصة ومعارف ----
    def synthesize_insight(self, topic: str, materials: List[Dict]) -> Optional[Insight]:
        if not materials:
            return None
        joined = "\n\n".join(f"- {m['chunk'][:1500]}" for m in materials[:5])
        prompt = f"""لخّص بدقة وبالعربية الأفكار الجوهرية حول "{topic}". 
        أخرج نقاطًا عملية، وخلاصة نهائية قصيرة (<= 60 كلمة)، واذكر تحذيرات أو محاذير إن وُجدت."""
        if USE_OPENAI or USE_GEMINI:
            summary = self.llm_summarize(prompt + "\n\nمواد:\n" + joined)
        else:
            # ملخص بسيط بديل (extractive): أول/وسط/آخر جملة
            sentences = [s.strip() for s in joined.split(". ") if len(s.strip()) > 40]
            pick = [sentences[0], sentences[len(sentences)//2], sentences[-1]] if len(sentences) >= 3 else sentences[:3]
            summary = " ".join(pick)[:900]
        confidence = min(0.9, 0.6 + 0.05 * len(materials))
        sources = list({m["title"] for m in materials})[:5]
        return Insight(
            topic=topic,
            summary=summary,
            confidence=confidence,
            sources=sources,
            created_at=datetime.utcnow(),
        )

    # ---- انعكاس ذاتي وتخطيط الجولة التالية ----
    def reflect(self, goal: str, insight: Insight) -> str:
        base = f"هدفنا: {goal}\nخلاصة الجولة: {insight.summary[:260]}..."
        q = f"ما الفجوات المعرفية؟ اقترح استعلامًا أعمق واحدًا."
        if USE_OPENAI or USE_GEMINI:
            res = self.llm_generate(base + "\n" + q)
            return res[0] if res else ""
        # بديل بسيط
        return "limitations challenges comparison benchmark implementation tutorial"

    # ---- واجهات LLM الاختيارية ----
    def llm_generate(self, prompt: str) -> List[str]:
        try:
            if USE_OPENAI:
                rsp = openai_client.chat.completions.create(
                    model=os.getenv("OPENAI_MODEL", self.cfg["llm"]["model"]),
                    messages=[{"role":"user","content":prompt}],
                    temperature=self.cfg["llm"].get("temperature", 0.2),
                    max_tokens=self.cfg["llm"].get("max_tokens", 800),
                )
                text = rsp.choices[0].message.content.strip()
                return [l.strip("-• ").strip() for l in text.split("\n") if l.strip()]
            if USE_GEMINI:
                model = os.getenv("GEMINI_MODEL", self.cfg["llm"]["model"])
                gen = genai.GenerativeModel(model)
                out = gen.generate_content(prompt)
                text = out.text or ""
                return [l.strip("-• ").strip() for l in text.split("\n") if l.strip()]
        except Exception:
            return []
        return []

    def llm_summarize(self, prompt: str) -> str:
        try:
            if USE_OPENAI:
                rsp = openai_client.chat.completions.create(
                    model=os.getenv("OPENAI_MODEL", self.cfg["llm"]["model"]),
                    messages=[{"role":"user","content":prompt}],
                    temperature=0.2, max_tokens=700,
                )
                return rsp.choices[0].message.content.strip()
            if USE_GEMINI:
                model = os.getenv("GEMINI_MODEL", self.cfg["llm"]["model"])
                gen = genai.GenerativeModel(model)
                out = gen.generate_content(prompt)
                return (out.text or "").strip()
        except Exception:
            pass
        return ""
