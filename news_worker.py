# -*- coding: utf-8 -*-
import os, time, feedparser
from memory import Memory
from fetcher import fetch_and_clean
from learner import Learner
from searcher import web_search

DB = os.getenv("AUTOLEARN_DB", "autolearn.db")
INTERVAL = int(os.getenv("UPDATE_INTERVAL", "60"))  # ثوانٍ
LANG = os.getenv("LANGUAGE", "ar")

RSS_LIST = [
  "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml",
  "https://feeds.arstechnica.com/arstechnica/technology-lab",
  "https://www.theverge.com/rss/index.xml",
]

def run():
    mem = Memory(DB); mem.init()
    L = Learner(mem)
    while True:
        try:
            # RSS
            for url in RSS_LIST:
                feed = feedparser.parse(url)
                for e in feed.entries[:5]:
                    link = getattr(e, "link", None)
                    title = getattr(e, "title", "")
                    if not link or mem.doc_exists(link): continue
                    text = fetch_and_clean(link)
                    if not text: continue
                    doc_id = mem.add_doc(url=link, title=title, text=text, source="rss", lang=LANG)
                    L.process_doc(doc_id, text)
            # بحث عام
            for q in ["أحدث أخبار الذكاء الاصطناعي", "ابتكارات الاتصالات", "هندسة البرمجيات"]:
                for r in web_search(q, max_results=3):
                    if mem.doc_exists(r["href"]): continue
                    t = fetch_and_clean(r["href"])
                    if not t: continue
                    doc_id = mem.add_doc(url=r["href"], title=r["title"], text=t, source="web", lang=LANG)
                    L.process_doc(doc_id, t)
        except Exception as e:
            print("[news_worker] error:", e)
        time.sleep(INTERVAL)

if __name__ == "__main__":
    run()
