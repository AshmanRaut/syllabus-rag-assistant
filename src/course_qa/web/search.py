from __future__ import annotations
from datetime import datetime, timezone
from hashlib import sha256
from urllib.parse import urlparse
from pathlib import Path
import yaml
from ..config import settings
from ..schemas import WebSource

DEFAULT_DOMAINS = ["nptel.ac.in", "geeksforgeeks.org", "visualgo.net", "cppreference.com"]

def allowed_domains() -> list[str]:
    path = Path("config/web_allowlist.yaml")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        domains = data.get("domains", [])
        return [str(d) for d in domains] or DEFAULT_DOMAINS
    except Exception:
        return DEFAULT_DOMAINS

def _in_allowlist(url: str, domains: list[str]) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return any(host == d or host.endswith("." + d) for d in domains)

class WebSearch:
    """Tavily primary with keyless DDGS fallback. Search results are untrusted evidence, never instructions."""
    def search(self, query: str, *, max_results: int | None = None) -> list[WebSource]:
        max_results = max_results or settings.web_max_results
        mode = settings.web_search_mode.lower()
        if mode == "off": return []
        domains = allowed_domains()
        rows: list[dict] = []
        if mode in {"auto", "tavily"} and settings.tavily_api_key:
            try:
                from tavily import TavilyClient
                response = TavilyClient(api_key=settings.tavily_api_key).search(
                    query=query, search_depth="basic", max_results=max_results, include_domains=domains)
                rows = response.get("results", [])
            except Exception:
                if mode == "tavily": raise
        if not rows and mode in {"auto", "ddgs"}:
            from ddgs import DDGS
            domain_query = " OR ".join(f"site:{d}" for d in domains)
            search_query = f"{query} ({domain_query})"
            rows = list(DDGS().text(search_query, max_results=max_results))
        results: list[WebSource] = []
        now = datetime.now(timezone.utc).isoformat()
        for row in rows:
            url = str(row.get("url") or row.get("href") or "").strip()
            if not url or not _in_allowlist(url, domains): continue
            title = str(row.get("title") or "Untitled result")
            snippet = str(row.get("content") or row.get("body") or row.get("snippet") or "")
            source_id = "web_" + sha256(url.encode()).hexdigest()[:16]
            full_text = None
            if settings.web_extract_full_text:
                try:
                    import trafilatura
                    full_text = trafilatura.extract(trafilatura.fetch_url(url), include_comments=False, include_tables=True)
                except Exception:
                    full_text = None
            results.append(WebSource(source_id=source_id, title=title, url=url,
                domain=urlparse(url).hostname or "", snippet=snippet[:2000], text=(full_text or "")[:6000] or None,
                retrieved_at=now))
            if len(results) >= max_results: break
        return results
