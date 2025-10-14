# -*- coding: utf-8 -*-
import os, time, hashlib, threading, datetime as dt
from typing import List, Optional
from fastapi import FastAPI, Query
from pydantic import BaseModel

from memory import Memory
from searcher import web_search
from fetcher import fetch_and_clean
from learner import Learner

LANG = os.getenv("LANGUAGE", "ar")
UPDATE_INTERVAL = int(os.getenv("UPDATE_INTERVAL", "5"))  # دقائق
AUTONOMOUS = os.getenv("AUTONOMOUS_MODE", "true").lower() == "true"

app = FastAPI(title="AutoLearn Core", version="1.0")

mem = Memory(os.getenv("AUTOLEARN_DB", "autolearn.db"))
learner = Learner(mem)

DEFAULT_TOPICS = os.getenv(
    "LEARNING_PRIORITIES",
    "technology,education,network,telecom,software,energy,science,ai,robotics"
).split(",")

class AskRequest(BaseModel):
    q: str
    k: int = 6

def _now(): return dt.datetime.utcnow().isoformat(timespec="seconds") + "Z"

def learn_once():
    topics = [t.strip() for t in DEFAULT_TOPICS if t.strip()]
    for topic in topics:
        for q in (f"أحدث الأخبار عن {topic}", f"شرح {topic} للمبتدئين"):
            results = web_search(q, max_results=5)
            for r in results:
                url, title = r["href"], r["title"]
                if mem.doc_exists(url): 
                    continue
                text = fetch_and_clean(url)
                if not text or len(text) < 400:
                    continue
                doc_id = mem.add_doc(url=url, title=title, text=text, source="web", lang=LANG)
                learner.process_doc(doc_id, text)

class LoopThread(threading.Thread):
    daemon = True
    def run(self):
        while True:
            try:
                learn_once()
            except Exception as e:
                print("[learn-loop] error:", e)
            time.sleep(UPDATE_INTERVAL * 60)

@app.on_event("startup")
def _startup():
    mem.init()
    if AUTONOMOUS:
        LoopThread().start()

@app.get("/health")
def health():
    return {"ok": True, "time": _now()}

@app.get("/learn/status")
def learn_status():
    s = mem.stats()
    s["interval_minutes"] = UPDATE_INTERVAL
    s["autonomous"] = AUTONOMOUS
    return s

@app.get("/search")
def search_api(q: str = Query(..., description="عبارة البحث"), n: int = 5):
    return web_search(q, max_results=n)

@app.post("/chat")
def chat(req: AskRequest):
    hits = mem.search_chunks(req.q, top_k=req.k)
    answer = learner.answer_from_chunks(req.q, hits)
    return {"question": req.q, "answer": answer, "hits": hits}
