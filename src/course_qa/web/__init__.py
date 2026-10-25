"""Web search sub-package.

Public API:
    WebSearch     – Tavily primary / DDGS fallback web searcher
    allowed_domains  – Returns the current domain allowlist
    _in_allowlist    – URL membership check (useful for testing)
"""
from .search import WebSearch, allowed_domains, _in_allowlist

__all__ = ["WebSearch", "allowed_domains", "_in_allowlist"]
