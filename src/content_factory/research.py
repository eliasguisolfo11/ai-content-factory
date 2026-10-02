from __future__ import annotations

import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen

WIKI_API = "https://es.wikipedia.org/w/api.php"
EN_WIKI_API = "https://en.wikipedia.org/w/api.php"
HEADERS = {"User-Agent": "AIContentFactoryMVP/0.1 (educational research workflow)"}


def _search(api: str, query: str, limit: int = 5) -> list[dict]:
    params = urlencode({"action": "query", "list": "search", "srsearch": query,
                        "format": "json", "srlimit": limit})
    request = Request(f"{api}?{params}", headers=HEADERS)
    with urlopen(request, timeout=20) as response:
        return json.loads(response.read()).get("query", {}).get("search", [])


def collect_sources(topic: str, limit: int = 6) -> list[dict]:
    """Collect encyclopedia references as research leads, not as a truth oracle."""
    found: list[dict] = []
    seen: set[str] = set()
    for api, lang in ((WIKI_API, "es"), (EN_WIKI_API, "en")):
        for row in _search(api, topic, limit=limit):
            title = row.get("title", "")
            url = f"https://{'es' if lang == 'es' else 'en'}.wikipedia.org/wiki/" + title.replace(" ", "_")
            if url in seen:
                continue
            seen.add(url)
            found.append({"id": f"S{len(found)+1:02d}", "title": title, "url": url,
                          "language": lang, "extract": row.get("snippet", "").replace('<span class="searchmatch">', "").replace("</span>", ""),
                          "source_type": "encyclopedia lead; verify against cited references"})
            if len(found) >= limit:
                return found
    return found
