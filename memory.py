import sqlite3, json, os, time
from typing import List, Tuple, Optional
import numpy as np
from sklearn.neighbors import NearestNeighbors

EMB_DIM = 384  # all-MiniLM-L6-v2

class VectorIndex:
    def __init__(self, vectors: np.ndarray):
        self.vectors = vectors.astype("float32") if vectors.size else np.zeros((0, EMB_DIM), dtype="float32")
        self.nn = None
        if len(self.vectors):
            self.nn = NearestNeighbors(n_neighbors=min(10, len(self.vectors)), metric="cosine").fit(self.vectors)

    def search(self, qvec: np.ndarray, topk: int = 8):
        if self.nn is None or self.vectors.size == 0:
            return [], []
        dists, idxs = self.nn.kneighbors(qvec.reshape(1, -1), n_neighbors=min(topk, len(self.vectors)))
        sims = 1 - dists[0]
        return idxs[0].tolist(), sims.tolist()

class Memory:
    def __init__(self, db_path="autolearn.db"):
        self.db = sqlite3.connect(db_path)
        self.db.execute("""CREATE TABLE IF NOT EXISTS docs(
            id INTEGER PRIMARY KEY, url TEXT UNIQUE, title TEXT, text TEXT,
            published TEXT, fetched_at TEXT
        )""")
        self.db.execute("""CREATE TABLE IF NOT EXISTS chunks(
            id INTEGER PRIMARY KEY, doc_id INTEGER, chunk_ix INTEGER,
            text TEXT, vector BLOB,
            FOREIGN KEY(doc_id) REFERENCES docs(id)
        )""")
        self.db.execute("""CREATE TABLE IF NOT EXISTS insights(
            id INTEGER PRIMARY KEY, topic TEXT, summary TEXT, confidence REAL,
            sources TEXT, created_at TEXT
        )""")
        self.db.commit()

    def upsert_doc(self, url: str, title: str, text: str, published: Optional[str], fetched_at: str) -> int:
        cur = self.db.cursor()
        cur.execute("INSERT OR IGNORE INTO docs(url,title,text,published,fetched_at) VALUES(?,?,?,?,?)",
                    (url, title, text, published, fetched_at))
        self.db.commit()
        cur.execute("SELECT id FROM docs WHERE url=?", (url,))
        return cur.fetchone()[0]

    def add_chunk(self, doc_id: int, chunk_ix: int, text: str, vec: np.ndarray):
        self.db.execute("INSERT INTO chunks(doc_id,chunk_ix,text,vector) VALUES(?,?,?,?)",
                        (doc_id, chunk_ix, text, vec.tobytes()))
        self.db.commit()

    def load_index(self) -> Tuple[VectorIndex, List[Tuple[int, int]]]:
        rows = self.db.execute("SELECT id,doc_id,chunk_ix,vector FROM chunks ORDER BY id ASC").fetchall()
        vectors, mapping = [], []
        for cid, did, cix, vbytes in rows:
            vec = np.frombuffer(vbytes, dtype="float32")
            vectors.append(vec)
            mapping.append((cid, did))
        mat = np.vstack(vectors) if vectors else np.zeros((0, EMB_DIM), dtype="float32")
        return VectorIndex(mat), mapping

    def get_chunk_text(self, chunk_id: int) -> str:
        row = self.db.execute("SELECT text FROM chunks WHERE id=?", (chunk_id,)).fetchone()
        return row[0] if row else ""

    def store_insight(self, topic: str, summary: str, confidence: float, sources: List[str], created_at: str) -> int:
        cur = self.db.cursor()
        cur.execute("INSERT INTO insights(topic,summary,confidence,sources,created_at) VALUES(?,?,?,?,?)",
                    (topic, summary, confidence, json.dumps(sources, ensure_ascii=False), created_at))
        self.db.commit()
        return cur.lastrowid

    def top_similar(self, qvec: np.ndarray, topk=8):
        index, mapping = self.load_index()
        idxs, sims = index.search(qvec, topk)
        results = []
        for i, s in zip(idxs, sims):
            cid, did = mapping[i]
            txt = self.get_chunk_text(cid)
            results.append((cid, did, s, txt))
        return results
