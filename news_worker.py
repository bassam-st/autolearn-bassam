# news_worker.py
import os, re, time, argparse, sqlite3, datetime as dt
import requests, feedparser, yaml
from urllib.parse import urlparse
from readability import Document
from lxml.html.clean import Cleaner

CONFIG_PATH = os.path.join(os.getcwd(), "config.yaml")
DB_PATH = os.getenv("AUTOLEARN_DB", "/data/autolearn.db")

HTML_CLEANER = Cleaner(
    style=True, links=False, remove_unknown_tags=False,
    javascript=True, scripts=True, page_structure=False
)

def load_cfg():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def ensure_db():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS docs(
        id INTEGER PRIMARY KEY,
        url TEXT UNIQUE,
        title TEXT,
        source TEXT,
        created_at TEXT,
        text TEXT
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS chunks(
        id INTEGER PRIMARY KEY,
        doc_id INTEGER,
        chunk_index INTEGER,
        text TEXT,
        FOREIGN KEY(doc_id) REFERENCES docs(id)
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS insights(
        id INTEGER PRIMARY KEY,
        doc_id INTEGER,
        summary TEXT,
        created_at TEXT,
        FOREIGN KEY(doc_id) REFERENCES docs(id)
    )""")
    con.commit(); con.close()

def fetch_url_clean(url, timeout=12):
    try:
        r = requests.get(url, timeout=timeout, headers={"User-Agent":"Mozilla/5.0"})
        r.raise_for_status()
        doc = Document(r.text)
        title = doc.short_title() or url
        html = HTML_CLEANER.clean_html(doc.summary())
        text = re.sub(r"\s+", " ", re.sub("<[^>]+>", " ", html)).strip()
        return title, text
    except Exception:
        return None, None

def is_blocked(url, blocked_domains):
    host = urlparse(url).hostname or ""
    return any(bd in host for bd in blocked_domains)

def add_doc(url, title, text, source):
    if not text or len(text) < 200: 
        return None
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    try:
        cur.execute("INSERT OR IGNORE INTO docs(url,title,source,created_at,text) VALUES (?,?,?,?,?)",
                    (url, title or url, source, dt.datetime.utcnow().isoformat(), text))
        con.commit()
        cur.execute("SELECT id FROM docs WHERE url=?", (url,))
        doc_id = cur.fetchone()[0]
    except Exception:
        con.close()
        return None
    # chunking بسيط ~1200 حرف
    size = 1200
    chunks = [text[i:i+size] for i in range(0, len(text), size)]
    for i, ch in enumerate(chunks):
        cur.execute("INSERT INTO chunks(doc_id,chunk_index,text) VALUES(?,?,?)", (doc_id, i, ch))
    # تلخيص بسيط (أول 40-60 كلمة)
    words = re.findall(r"\w+", text)
    summary = " ".join(words[:60]) + ("..." if len(words) > 60 else "")
    cur.execute("INSERT INTO insights(doc_id,summary,created_at) VALUES(?,?,?)",
                (doc_id, summary, dt.datetime.utcnow().isoformat()))
    con.commit(); con.close()
    return doc_id

def crawl_rss(url, cfg):
    blocked = cfg.get("blocked_domains", []) or []
    try:
        feed = feedparser.parse(url)
        for e in feed.entries[:10]:
            link = getattr(e, "link", None) or getattr(e, "id", None)
            if not link or is_blocked(link, blocked): 
                continue
            title, text = fetch_url_clean(link)
            if title and text:
                add_doc(link, title, text, source="rss")
    except Exception as ex:
        print("RSS error:", url, ex)

def crawl_arxiv(cat, cfg):
    rss = f"https://export.arxiv.org/rss/{cat}"
    crawl_rss(rss, cfg)

def crawl_wikipedia(keywords, cfg):
    # نبسّط: نأخذ صفحة بحث ويكي الأولى ونجرّب أول نتيجة
    for kw in keywords[:3]:
        try:
            s = requests.get("https://ar.wikipedia.org/w/index.php",
                             params={"search": kw}, timeout=12).text
            m = re.search(r'href="(/wiki/[^"]+)"', s)
            if not m: 
                continue
            url = "https://ar.wikipedia.org" + m.group(1)
            title, text = fetch_url_clean(url)
            if title and text:
                add_doc(url, title, text, source="wikipedia")
        except Exception as ex:
            print("Wikipedia error:", kw, ex)

def crawl_personal_files(cfg):
    folder = cfg.get("personal_files_dir", "/data/inbox")
    try:
        os.makedirs(folder, exist_ok=True)
        for fn in os.listdir(folder):
            if not fn.lower().endswith((".txt", ".md")):
                continue
            path = os.path.join(folder, fn)
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
            if len(text) < 50: 
                continue
            url = f"file://{path}"
            add_doc(url, os.path.splitext(fn)[0], text, source="personal")
    except Exception as ex:
        print("Personal files error:", ex)

def run_cycle():
    cfg = load_cfg()
    ensure_db()

    # RSS
    for rss in cfg.get("rss_feeds", []):
        crawl_rss(rss, cfg)

    # arXiv
    for cat in cfg.get("arxiv_queries", []):
        crawl_arxiv(cat, cfg)

    # ويكيبيديا (بالكلمات المفتاحية)
    crawl_wikipedia(cfg.get("learning_keywords", []), cfg)

    # ملفات شخصية
    crawl_personal_files(cfg)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--loop", action="store_true")
    ap.add_argument("--interval", type=int, default=10)
    args = ap.parse_args()

    if args.once:
        print("▶️ Running single learning cycle ...")
        run_cycle()
    elif args.loop:
        print(f"🔁 Loop mode every {args.interval} min")
        while True:
            run_cycle()
            time.sleep(args.interval * 60)
    else:
        # افتراضي: دورة واحدة
        run_cycle()

if __name__ == "__main__":
    main()
