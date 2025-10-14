# -*- coding: utf-8 -*-
import requests, readability, lxml.html, re
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0 (AutoLearn/1.0)"}

def clean_html(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script","style","noscript"]): tag.decompose()
    text = soup.get_text(separator="\n")
    text = re.sub(r"\n{2,}", "\n", text)
    return text.strip()

def fetch_and_clean(url: str) -> str:
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        r.raise_for_status()
        doc = readability.Document(r.text)
        main_html = doc.summary()
        return clean_html(main_html)
    except Exception:
        return ""
