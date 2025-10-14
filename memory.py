# -*- coding: utf-8 -*-
import os, sqlite3, hashlib, numpy as np
from typing import List, Dict
from sklearn.metrics.pairwise import cosine_similarity

class Memory:
    def __init__(self, db_path: str = "autolearn.db"):
        import os
self.db_path = db_path or os.getenv("AUTOLEARN_DB", "/data/autolearn.db")

    def init(self):
        con = sqlite3.connect(self.db_path); cur = con.cursor()
        cur.execute("""CREATE TABLE IF NOT EXISTS docs(
            id INTEGER PRIMARY KEY, url TEXT UNIQUE, title TEXT, text TEXT,
            source TEXT, lang TEXT, h TEXT)""")
        cur.execute("""CREATE TABLE IF NOT EXISTS chunks(
            id INTEGER PRIMARY KEY, doc_id INTEGER, text TEXT, emb BLOB)""")
        cur.execute("""CREATE TABLE IF NOT EXISTS insights(
            id INTEGER PRIMARY KEY, doc_id INTEGER, text TEXT)""")
        con.commit(); con.close()

    def _hash(self, s: str) -> str: return hashlib.sha256(s.encode("utf-8")).hexdigest()

    def doc_exists(self, url: str) -> bool:
        con = sqlite3.connect(self.db_path); cur = con.cursor()
        cur.execute("SELECT 1 FROM docs WHERE url=? LIMIT 1", (url,))
        ok = cur.fetchone() is not None; con.close(); return ok

    def add_doc(self, url: str, title: str, text: str, source: str, lang: str) -> int:
        h = self._hash(url)
        con = sqlite3.connect(self.db_path); cur = con.cursor()
        cur.execute("INSERT OR IGNORE INTO docs(url,title,text,source,lang,h) VALUES(?,?,?,?,?,?)",
                    (url, title, text, source, lang, h))
        con.commit()
        cur.execute("SELECT id FROM docs WHERE url=?", (url,))
        doc_id = cur.fetchone()[0]; con.close(); return doc_id

    def add_chunk(self, doc_id: int, text: str, emb_bytes: bytes):
        con = sqlite3.connect(self.db_path); cur = con.cursor()
        cur.execute("INSERT INTO chunks(doc_id,text,emb) VALUES(?,?,?)", (doc_id, text, emb_bytes))
        con.commit(); con.close()

    def add_insight(self, doc_id: int, text: str):
        con = sqlite3.connect(self.db_path); cur = con.cursor()
        cur.execute("INSERT INTO insights(doc_id,text) VALUES(?,?)", (doc_id, text))
        con.commit(); con.close()

    def stats(self) -> Dict:
        con = sqlite3.connect(self.db_path); cur = con.cursor()
        def c(t):
            try: return cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            except: return 0
        size_mb = round(os.path.getsize(self.db_path)/(1024*1024), 3) if os.path.exists(self.db_path) else 0
        out = {"db_exists": os.path.exists(self.db_path), "size_mb": size_mb,
               "docs": c("docs"), "chunks": c("chunks"), "insights": c("insights")}
        con.close(); return out

    def search_chunks(self, query: str, top_k: int = 6) -> List[Dict]:
        # اجلب كل المتجهات (لمشروع صغير تكفي – لاحقًا استبدلها بFAISS)
        con = sqlite3.connect(self.db_path); cur = con.cursor()
        cur.execute("SELECT id, text, emb FROM chunks")
        rows = cur.fetchall(); con.close()
        if not rows: return []
        texts, embs, ids = [], [], []
        for cid, text, emb in rows:
            ids.append(cid); texts.append(text); embs.append(np.frombuffer(emb, dtype=np.float32))
        Q = np.array([np.frombuffer(b"", dtype=np.float32)])  # dummy to init shape
        # تقريبي: استخدم نفس دالة التجزئة كتمثيل للبحث بدون نموذج (يمكن تحسينه)
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        qv = model.encode([query], normalize_embeddings=True)
        S = cosine_similarity(qv, np.vstack(embs)).ravel()
        idx = np.argsort(S)[::-1][:top_k]
        return [{"chunk_id": int(ids[i]), "text": texts[i], "score": float(S[i])} for i in idx]
