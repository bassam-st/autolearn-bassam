from duckduckgo_search import DDGS
from dateutil import parser as dateparser
from datetime import datetime, timedelta
from typing import List, Optional
from schemas import SearchHit

def _parse_date(d) -> Optional[datetime]:
    try:
        return dateparser.parse(d)
    except Exception:
        return None

class WebSearcher:
    def __init__(self, days: int = 365, blocked_domains=None):
        self.days = days
        self.blocked = set(blocked_domains or [])

    def search(self, query: str, max_results: int = 5) -> List[SearchHit]:
        hits = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results, safesearch="moderate", region="wt-wt"):
                url = r.get("href") or r.get("url")
                if not url or any(b in url for b in self.blocked):
                    continue
                t = r.get("title", "")
                snippet = r.get("body", "")
                dt = _parse_date(r.get("date"))
                hits.append(SearchHit(title=t, url=url, snippet=snippet, published=dt, source="ddg"))
        # فضّل الأحدث
        cutoff = datetime.utcnow() - timedelta(days=self.days)
        hits.sort(key=lambda h: (h.published or cutoff, h.title), reverse=True)
        return hits
