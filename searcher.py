from duckduckgo_search import DDGS

def web_search(query: str, max_results: int = 5):
    out = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=max_results, region="wt-wt", safesearch="moderate"):
            if r.get("href"):
                out.append({"title": r.get("title",""), "href": r["href"]})
    return out
