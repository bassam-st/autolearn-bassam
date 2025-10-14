# -*- coding: utf-8 -*-
import numpy as np, re
from typing import List, Dict
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
from memory import Memory

class Learner:
    def __init__(self, mem: Memory):
        self.mem = mem
        self.model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

    def _chunk(self, text: str, size: int = 800, overlap: int = 120) -> List[str]:
        words = re.split(r"\s+", text)
        i, out = 0, []
        while i < len(words):
            out.append(" ".join(words[i:i+size]))
            i += (size - overlap)
        return [c for c in out if len(c.split()) > 30]

    def process_doc(self, doc_id: int, text: str):
        chunks = self._chunk(text)
        if not chunks: return
        embeds = self.model.encode(chunks, normalize_embeddings=True)
        for ch, emb in zip(chunks, embeds):
            self.mem.add_chunk(doc_id, ch, emb.astype(np.float32).tobytes())
        # insight بسيط: أهم الجُمل TF-IDF
        top = self.top_sentences(text, k=3)
        for s in top:
            self.mem.add_insight(doc_id, s)

    def top_sentences(self, text: str, k: int = 3) -> List[str]:
        sents = re.split(r"(?<=[.!؟])\s+", text)
        vec = TfidfVectorizer(max_features=2000).fit_transform(sents)
        scores = vec.sum(axis=1).A.ravel()
        idx = np.argsort(scores)[::-1][:k]
        return [sents[i] for i in idx if sents[i].strip()]

    def answer_from_chunks(self, question: str, hits: List[Dict]) -> str:
        if not hits: return "لم أعثر على إجابة كافية بعد."
        context = "\n\n".join([h["text"] for h in hits])
        # إجابة توليدية مبسّطة بدون LLM:
        return f"مختصر الإجابة:\n{self.top_sentences(context, k=2)[0]}\n\n— (اعتمدت على {len(hits)} مقطع من الذاكرة)"
