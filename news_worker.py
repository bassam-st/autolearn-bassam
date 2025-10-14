import time, hashlib, sqlite3, feedparser, requests, re
from datetime import datetime, timezone

DB = os.getenv("AUTOLEARN_DB", "/data/autolearn.db") if "AUTOLEARN_DB" in os.environ else "autolearn.db"
INTERVAL_SEC = 60
FEEDS = [
  "https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en",
  "https://feeds.arstechnica.com/arstechnica/index",
  "https://www.reuters.com/rssFeed/technologyNews",
  "https://www.theguardian.com/world/rss",
  "https://www.nature.com/nature.rss",
  "https://hnrss.org/frontpage"
]

def strip_html(t): return re.sub("<[^<]+?>", " ", t or "").strip()

def ensure_db():
    con = sqlite3.connect(DB); c = con.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS docs(
        id TEXT PRIMARY KEY, url TEXT, title TEXT, created_at TEXT, tag TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS chunks(
        id TEXT PRIMARY KEY, doc_id TEXT, text TEXT, created_at TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS insights(
        id TEXT PRIMARY KEY, text TEXT, created_at TEXT, tag TEXT)""")
    con.commit(); con.close()

def save_news(url, title, summary):
    doc_id = hashlib.sha1(url.encode()).hexdigest()
    ch_id  = hashlib.sha1((url+"#chunk").encode()).hexdigest()
    now = datetime.now(timezone.utc).isoformat()
    con = sqlite3.connect(DB); c = con.cursor()
    c.execute("INSERT OR IGNORE INTO docs(id,url,title,created_at,tag) VALUES(?,?,?,?,?)",
              (doc_id,url,title,now,"news"))
    text = f"{title}\n\n{summary}\n\nSource: {url}"
    c.execute("INSERT OR IGNORE INTO chunks(id,doc_id,text,created_at) VALUES(?,?,?,?)",
              (ch_id,doc_id,text,now))
    con.commit(); con.close()

def run():
    ensure_db()
    while True:
        try:
            for feed in FEEDS:
                d = feedparser.parse(feed)
                for e in d.entries[:10]:
                    url, title = e.link, e.title
                    summary = strip_html(getattr(e, "summary", "")) or title
                    save_news(url, title, summary)
            print("[NewsWorker] tick ok")
        except Exception as ex:
            print("[NewsWorker] error:", ex)
        time.sleep(INTERVAL_SEC)

if __name__ == "__main__":
    run()
