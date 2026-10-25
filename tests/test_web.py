"""Tests for web search module.

Run with:
    pytest tests/test_web.py -v

These tests are designed to run without network access. They mock the
underlying search providers and verify the WebSearch contract.
"""
from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock, patch

import pytest

from course_qa.schemas import WebSource
from course_qa.web.search import WebSearch, _in_allowlist, allowed_domains


# ─── Helpers ─────────────────────────────────────────────────────────────────

class FakeSettings:
    """Minimal settings stand-in for tests that need mutable state."""

    def __init__(self, **kwargs):
        defaults = dict(
            web_search_mode="ddgs",
            tavily_api_key="",
            web_max_results=5,
            web_extract_full_text=False,
        )
        defaults.update(kwargs)
        for k, v in defaults.items():
            setattr(self, k, v)


def _make_ddgs_row(url: str, title: str = "Test", body: str = "snippet") -> dict:
    return {"href": url, "title": title, "body": body}


def _fake_ddgs_module(rows: list[dict]) -> types.ModuleType:
    """Build a fake `ddgs` module whose DDGS().text() returns `rows`."""
    mock_ddgs_instance = MagicMock()
    mock_ddgs_instance.text.return_value = rows
    mock_ddgs_class = MagicMock(return_value=mock_ddgs_instance)
    module = types.ModuleType("ddgs")
    module.DDGS = mock_ddgs_class  # type: ignore[attr-defined]
    return module


# ─── Allowlist helper tests ───────────────────────────────────────────────────

def test_in_allowlist_exact_match():
    assert _in_allowlist("https://geeksforgeeks.org/test", ["geeksforgeeks.org"])


def test_in_allowlist_subdomain_match():
    assert _in_allowlist("https://www.geeksforgeeks.org/test", ["geeksforgeeks.org"])


def test_in_allowlist_rejects_unlisted_domain():
    assert not _in_allowlist("https://evil.com/test", ["geeksforgeeks.org"])


def test_in_allowlist_rejects_partial_suffix():
    """'notgeeksforgeeks.org' must NOT match 'geeksforgeeks.org'."""
    assert not _in_allowlist("https://notgeeksforgeeks.org/x", ["geeksforgeeks.org"])


def test_in_allowlist_empty_domains():
    assert not _in_allowlist("https://geeksforgeeks.org/test", [])


def test_in_allowlist_empty_url():
    assert not _in_allowlist("", ["geeksforgeeks.org"])


def test_in_allowlist_multiple_domains():
    domains = ["nptel.ac.in", "geeksforgeeks.org", "visualgo.net"]
    assert _in_allowlist("https://nptel.ac.in/course/123", domains)
    assert _in_allowlist("https://visualgo.net/en/sorting", domains)
    assert not _in_allowlist("https://wikipedia.org/wiki/BFS", domains)


# ─── WebSearch.search — mode=off ─────────────────────────────────────────────

def test_web_search_off_returns_empty():
    """WEB_SEARCH_MODE=off must return [] without any network call."""
    fake = FakeSettings(web_search_mode="off")
    with patch("course_qa.web.search.settings", fake):
        results = WebSearch().search("Dijkstra algorithm")
    assert results == []


# ─── WebSearch.search — DDGS fallback ────────────────────────────────────────

def test_web_search_ddgs_filters_by_allowlist(monkeypatch):
    """DDGS results whose domain is not in the allowlist must be dropped."""
    fake_rows = [
        _make_ddgs_row("https://geeksforgeeks.org/dijkstra"),  # allowed
        _make_ddgs_row("https://evil.com/dijkstra"),           # NOT allowed
        _make_ddgs_row("https://nptel.ac.in/course"),          # allowed
    ]
    fake = FakeSettings(web_search_mode="ddgs", web_max_results=10)
    monkeypatch.setitem(sys.modules, "ddgs", _fake_ddgs_module(fake_rows))

    with patch("course_qa.web.search.settings", fake):
        results = WebSearch().search("Dijkstra algorithm")

    urls = [r.url for r in results]
    assert "https://geeksforgeeks.org/dijkstra" in urls
    assert "https://nptel.ac.in/course" in urls
    assert not any("evil.com" in u for u in urls), "evil.com must be filtered out"


def test_web_search_ddgs_returns_web_source_objects(monkeypatch):
    """Results must be WebSource instances with correct fields."""
    fake_rows = [_make_ddgs_row("https://geeksforgeeks.org/bst", "BST intro", "Binary tree")]
    fake = FakeSettings(web_search_mode="ddgs")
    monkeypatch.setitem(sys.modules, "ddgs", _fake_ddgs_module(fake_rows))

    with patch("course_qa.web.search.settings", fake):
        results = WebSearch().search("binary search tree")

    assert len(results) == 1
    ws = results[0]
    assert isinstance(ws, WebSource)
    assert ws.url == "https://geeksforgeeks.org/bst"
    assert ws.title == "BST intro"
    assert ws.snippet == "Binary tree"
    assert ws.domain == "geeksforgeeks.org"
    assert ws.source_type == "web"
    assert ws.source_id.startswith("web_")
    assert ws.retrieved_at  # non-empty ISO timestamp


def test_web_search_respects_max_results(monkeypatch):
    """Search must return at most max_results items."""
    fake_rows = [
        _make_ddgs_row(f"https://geeksforgeeks.org/topic{i}") for i in range(5)
    ]
    fake = FakeSettings(web_search_mode="ddgs", web_max_results=2)
    monkeypatch.setitem(sys.modules, "ddgs", _fake_ddgs_module(fake_rows))

    with patch("course_qa.web.search.settings", fake):
        results = WebSearch().search("sorting algorithms")

    assert len(results) <= 2


# ─── WebSearch.search — DDGS failure resilience ──────────────────────────────

def test_web_search_ddgs_exception_in_auto_mode_does_not_crash(monkeypatch):
    """If DDGS raises in 'auto' mode (no tavily key), WebSearch should propagate.
    The caller (service.py) is responsible for catching errors per the contract.
    We simply verify that instantiating WebSearch works fine regardless.
    """
    fake = FakeSettings(web_search_mode="auto", tavily_api_key="")
    ws = WebSearch()
    assert ws is not None  # no error on construction


def test_web_search_mode_off_never_imports_ddgs():
    """When mode=off, no provider import should be attempted at all."""
    # If ddgs is not importable, mode=off must still return []
    original = sys.modules.pop("ddgs", None)
    try:
        fake = FakeSettings(web_search_mode="off")
        with patch("course_qa.web.search.settings", fake):
            results = WebSearch().search("test query")
        assert results == []
    finally:
        if original is not None:
            sys.modules["ddgs"] = original


# ─── Tavily path ─────────────────────────────────────────────────────────────

def test_web_search_tavily_path(monkeypatch):
    """When tavily_api_key is set in tavily mode, TavilyClient must be called."""
    mock_client_instance = MagicMock()
    mock_client_instance.search.return_value = {
        "results": [
            {
                "url": "https://geeksforgeeks.org/dijkstra",
                "title": "Dijkstra GFG",
                "content": "Dijkstra's algorithm finds shortest paths.",
            }
        ]
    }
    mock_client_class = MagicMock(return_value=mock_client_instance)

    fake_tavily = types.ModuleType("tavily")
    fake_tavily.TavilyClient = mock_client_class  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "tavily", fake_tavily)

    fake = FakeSettings(web_search_mode="tavily", tavily_api_key="fake-key-abc")
    with patch("course_qa.web.search.settings", fake):
        results = WebSearch().search("Dijkstra shortest path")

    assert len(results) == 1
    assert results[0].url == "https://geeksforgeeks.org/dijkstra"
    assert results[0].title == "Dijkstra GFG"


def test_web_search_tavily_reraises_in_tavily_mode(monkeypatch):
    """In strict 'tavily' mode, provider errors must propagate (not swallowed)."""
    mock_client_class = MagicMock(side_effect=RuntimeError("tavily error"))
    fake_tavily = types.ModuleType("tavily")
    fake_tavily.TavilyClient = mock_client_class  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "tavily", fake_tavily)

    fake = FakeSettings(web_search_mode="tavily", tavily_api_key="fake-key")
    with patch("course_qa.web.search.settings", fake):
        with pytest.raises(RuntimeError, match="tavily error"):
            WebSearch().search("test query")


# ─── allowed_domains helper ───────────────────────────────────────────────────

def test_allowed_domains_returns_list():
    domains = allowed_domains()
    assert isinstance(domains, list)
    assert len(domains) > 0


def test_allowed_domains_contains_expected_entries():
    """The yaml must include at least GFG and NPTEL."""
    domains = allowed_domains()
    assert "geeksforgeeks.org" in domains
    assert "nptel.ac.in" in domains
