import requests, re
from bs4 import BeautifulSoup
from readability import Document
from datetime import datetime
from typing import Optional
from dateutil import parser as dateparser

UA = "Mozilla/5.0 (compatible; AutoLearn/1.0; +https://example.local)"

def _guess_published(html: str) -> Optional[str]:
    soup = BeautifulSoup(html, "lxml")
    candidates = [
        {"name": "article:published_time"},
        {"property": "article:published_time"},
        {"itemprop": "datePublished"},
        {"name": "pubdate"},
        {"property": "og:updated_time"},
    ]
    for c in candidates:
        tag = soup.find("meta", attrs=c)
        if tag and tag.get("content"):
            try:
                return dateparser.parse(tag["content"]).isoformat()
            except Exception:
                pass
    return None

def fetch_and_extract(url: str, max_bytes: int = 2_000_000):
    r = requests.get(url, headers={"User-Agent": UA}, timeout=20)
    r.raise_for_status()
    content = r.content[:max_bytes]
    html = content.decode(r.apparent_encoding or "utf-8", errors="ignore")
    doc = Document(html)
    title = doc.short_title()
    article_html = doc.summary(html_partial=True)
    soup = BeautifulSoup(article_html, "lxml")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = re.sub(r"\s+", " ", soup.get_text(" ", strip=True))
    published = _guess_published(html)
    return {
        "title": title or url,
        "text": text,
        "published": published,
        "fetched_at": datetime.utcnow().isoformat(timespec="seconds"),
    }
