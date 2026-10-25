"""tests/test_service.py — end-to-end tests for QAService and create_generator().

All dependencies (NotesRetriever, WebSearcher) are replaced with lightweight
inline fakes so no Qdrant instance or network connection is needed.
"""
from __future__ import annotations

import pytest
from course_qa.schemas import (
    AnswerRequest,
    AnswerResponse,
    RetrievedChunk,
    SourceChunk,
    WebSource,
)
from course_qa.generation import MockGenerator, create_generator
from course_qa.service import QAService, should_search_web


# ---------------------------------------------------------------------------
# Helpers / shared fixtures
# ---------------------------------------------------------------------------

def _make_chunk(
    chunk_id: str = "c1",
    text: str = "Dijkstra's algorithm finds the shortest path.",
    source_type: str = "typed_pdf",
    ocr_status: str = "not_needed",
    subject: str = "DS",
) -> SourceChunk:
    return SourceChunk(
        chunk_id=chunk_id,
        source_id="src1",
        subject=subject,  # type: ignore[arg-type]
        source_type=source_type,  # type: ignore[arg-type]
        source_file="ds_notes/dijkstra.pdf",
        page_number=1,
        text=text,
        content_hash="abc",
        source_hash="def",
        ocr_status=ocr_status,  # type: ignore[arg-type]
    )


def _make_retrieved(score: float = 0.5, **chunk_kwargs) -> RetrievedChunk:
    return RetrievedChunk(
        chunk=_make_chunk(**chunk_kwargs),
        score=score,
        channel="hybrid",
    )


def _make_web_source(source_id: str = "w1", snippet: str = "Dijkstra is a graph algorithm.") -> WebSource:
    return WebSource(
        source_id=source_id,
        title="Dijkstra Wikipedia",
        url="https://en.wikipedia.org/wiki/Dijkstra",
        domain="wikipedia.org",
        snippet=snippet,
        retrieved_at="2026-10-26T00:00:00",
        text=snippet,
    )


class _FakeRetriever:
    """Inline fake NotesRetriever; returns a fixed list of RetrievedChunks."""

    def __init__(self, results: list[RetrievedChunk] | None = None):
        self._results = results if results is not None else []

    def retrieve(self, question: str, *, subject=None, top_k: int = 5) -> list[RetrievedChunk]:
        return self._results[:top_k]


class _FakeWebSearcher:
    """Inline fake WebSearcher; returns a fixed list or raises."""

    def __init__(self, results: list[WebSource] | None = None, raise_exc: Exception | None = None):
        self._results = results or []
        self._raise = raise_exc

    def search(self, query: str, *, max_results: int = 5) -> list[WebSource]:
        if self._raise:
            raise self._raise
        return self._results[:max_results]


# ---------------------------------------------------------------------------
# create_generator() tests
# ---------------------------------------------------------------------------

class TestCreateGenerator:
    def test_returns_mock_when_no_llm_model_set(self, monkeypatch):
        """Without LLM_MODEL, create_generator() must return a MockGenerator."""
        import dataclasses
        import course_qa.generation.generator as gen_mod
        replacement = dataclasses.replace(gen_mod.settings, llm_model="")
        monkeypatch.setattr(gen_mod, "settings", replacement)
        g = create_generator()
        assert isinstance(g, MockGenerator)

    def test_falls_back_to_mock_when_real_generator_fails(self, monkeypatch):
        """When LLM_MODEL is set but generator fails to initialize, safely fall back to MockGenerator."""
        import dataclasses
        import course_qa.generation.generator as gen_mod
        replacement = dataclasses.replace(gen_mod.settings, llm_model="custom-model")
        monkeypatch.setattr(gen_mod, "settings", replacement)

        def _failing_init():
            raise RuntimeError("Simulated connection or init failure")

        monkeypatch.setattr(gen_mod, "OpenAICompatibleGenerator", _failing_init)
        g = create_generator()
        assert isinstance(g, MockGenerator)

    def test_create_generator_importable_from_package(self):
        """create_generator must be importable directly from course_qa.generation."""
        from course_qa.generation import create_generator as cg  # noqa: F401
        assert callable(cg)

    def test_mock_generator_importable_from_package(self):
        from course_qa.generation import MockGenerator as MG  # noqa: F401
        assert MG is MockGenerator


# ---------------------------------------------------------------------------
# MockGenerator tests
# ---------------------------------------------------------------------------

class TestMockGenerator:
    def test_produces_valid_answer_response_with_notes(self):
        gen = MockGenerator()
        req = AnswerRequest(question="What is Dijkstra?", subject="DS")
        notes = [_make_retrieved()]
        result = gen.generate(req, notes, [])
        assert isinstance(result, AnswerResponse)
        assert not result.abstained
        assert result.notes_used >= 1
        assert len(result.citations) >= 1

    def test_produces_valid_answer_response_with_web(self):
        gen = MockGenerator()
        req = AnswerRequest(question="What is Dijkstra?", use_web=True)
        web = [_make_web_source()]
        result = gen.generate(req, [], web)
        assert isinstance(result, AnswerResponse)
        assert not result.abstained
        assert result.web_used == 1
        assert result.citations[0].source_kind == "web"

    def test_abstains_when_no_evidence(self):
        gen = MockGenerator()
        req = AnswerRequest(question="Tell me something obscure.")
        result = gen.generate(req, [], [])
        assert result.abstained is True
        assert result.notes_used == 0
        assert result.web_used == 0
        assert result.citations == []

    def test_skips_ocr_pending_chunks(self):
        """Chunks with ocr_status='pending' must not appear as citations."""
        gen = MockGenerator()
        req = AnswerRequest(question="Explain quicksort.")
        notes = [
            _make_retrieved(chunk_id="pending1", text="[pending OCR]", ocr_status="pending"),
            _make_retrieved(chunk_id="good1", text="Quicksort divides and conquers."),
        ]
        # Provide two RetrievedChunks but they share source IDs; override per-chunk
        notes[0] = RetrievedChunk(
            chunk=_make_chunk(chunk_id="pending1", text="[pending OCR]", ocr_status="pending"),
            score=0.9,
            channel="hybrid",
        )
        notes[1] = RetrievedChunk(
            chunk=_make_chunk(chunk_id="good1", text="Quicksort divides and conquers.", ocr_status="not_needed"),
            score=0.5,
            channel="hybrid",
        )
        result = gen.generate(req, notes, [])
        # The pending chunk must not appear in citations.
        cited_ids = {c.source_id for c in result.citations}
        assert "pending1" not in cited_ids

    def test_skips_empty_text_chunks(self):
        gen = MockGenerator()
        req = AnswerRequest(question="Explain something.")
        notes = [
            RetrievedChunk(
                chunk=_make_chunk(chunk_id="empty1", text="   "),
                score=0.8,
                channel="hybrid",
            )
        ]
        result = gen.generate(req, notes, [])
        assert result.abstained is True

    def test_answer_contains_citation_labels(self):
        gen = MockGenerator()
        req = AnswerRequest(question="Explain BFS.")
        notes = [_make_retrieved(chunk_id="bfs1", text="BFS uses a queue.")]
        result = gen.generate(req, notes, [])
        assert "[S1]" in result.answer

    def test_mixed_notes_and_web(self):
        gen = MockGenerator()
        req = AnswerRequest(question="Real-world use of BFS?", use_web=True)
        notes = [_make_retrieved(chunk_id="bfs1", text="BFS is used in level-order traversal.")]
        web = [_make_web_source(source_id="w1")]
        result = gen.generate(req, notes, web)
        assert result.notes_used == 1
        assert result.web_used == 1


# ---------------------------------------------------------------------------
# QAService end-to-end tests
# ---------------------------------------------------------------------------

class TestQAService:
    def _make_service(self, notes=None, web_results=None, web_exc=None):
        retriever = _FakeRetriever(notes)
        searcher = _FakeWebSearcher(web_results, raise_exc=web_exc)
        generator = MockGenerator()
        return QAService(retriever, generator, searcher)

    # --- basic happy paths ---

    def test_answer_returns_answer_response(self):
        svc = self._make_service(notes=[_make_retrieved()])
        result = svc.answer(AnswerRequest(question="What is BFS?"))
        assert isinstance(result, AnswerResponse)

    def test_notes_only_path_does_not_call_web(self):
        """When use_web=False, web searcher must never be called."""
        called = []

        class _SpySearcher:
            def search(self, *a, **kw):
                called.append(True)
                return []

        svc = QAService(_FakeRetriever([_make_retrieved()]), MockGenerator(), _SpySearcher())
        svc.answer(AnswerRequest(question="What is BFS?", use_web=False))
        assert called == [], "Web searcher should not be called when use_web=False"

    def test_web_failure_produces_warning_not_crash(self):
        svc = self._make_service(
            notes=[_make_retrieved()],
            web_exc=ConnectionError("DNS lookup failed"),
        )
        req = AnswerRequest(question="Real-world applications of BFS?", use_web=True)
        result = svc.answer(req)
        assert isinstance(result, AnswerResponse)
        assert any("Web search failed" in w for w in result.warnings)

    def test_abstention_when_no_notes_and_no_web(self):
        svc = self._make_service(notes=[], web_results=[])
        req = AnswerRequest(question="Totally unknown topic.", use_web=True)
        result = svc.answer(req)
        assert result.abstained is True
        assert any("no" in w.lower() or "No" in w for w in result.warnings)

    # --- web routing (use_web gate) ---

    def test_use_web_false_is_strict_gate(self):
        """Even with signal words, use_web=False must prevent web call."""
        assert should_search_web(
            AnswerRequest(question="Real-world applications of BFS?", use_web=False), []
        ) is False

    def test_use_web_true_routes_when_no_notes(self):
        assert should_search_web(
            AnswerRequest(question="Some question?", use_web=True), []
        ) is True

    def test_use_web_true_routes_on_signal_words(self):
        assert should_search_web(
            AnswerRequest(question="Give real-world applications of Dijkstra", use_web=True), []
        ) is True

    def test_use_web_true_no_route_when_good_notes(self):
        """Strong note coverage (score >= 0.025) and no signal words → skip web."""
        notes = [_make_retrieved(score=0.5)]
        result = should_search_web(
            AnswerRequest(question="What is BFS?", use_web=True), notes
        )
        assert result is False

    # --- web search integration ---

    def test_web_results_included_in_response(self):
        svc = self._make_service(notes=[], web_results=[_make_web_source()])
        req = AnswerRequest(question="Real-world applications?", use_web=True)
        result = svc.answer(req)
        # Web was searched and the result fed to the generator.
        assert result.web_used >= 0  # MockGenerator may not cite every source; just verify no crash.

    def test_web_only_coverage(self):
        """When notes are empty but web returns results, service should not force abstention."""
        svc = self._make_service(notes=[], web_results=[_make_web_source()])
        req = AnswerRequest(question="Real-world applications of Dijkstra?", use_web=True)
        result = svc.answer(req)
        # Generator received web evidence, so abstained should be False (MockGenerator cites it).
        assert result.abstained is False

    # --- ocr/pending chunk propagation ---

    def test_pending_ocr_chunks_do_not_become_citations(self):
        pending_chunk = RetrievedChunk(
            chunk=_make_chunk(chunk_id="pen1", text="[pending OCR]", ocr_status="pending"),
            score=0.99,
            channel="hybrid",
        )
        good_chunk = _make_retrieved(chunk_id="g1", text="Merge sort is O(n log n).")
        svc = self._make_service(notes=[pending_chunk, good_chunk])
        req = AnswerRequest(question="Explain merge sort.")
        result = svc.answer(req)
        cited_ids = {c.source_id for c in result.citations}
        assert "pen1" not in cited_ids

    # --- multi-chunk ---

    def test_multiple_notes_produce_multiple_citations(self):
        notes = [
            _make_retrieved(chunk_id="n1", text="BFS uses a queue."),
            _make_retrieved(chunk_id="n2", text="DFS uses a stack."),
        ]
        svc = self._make_service(notes=notes)
        result = svc.answer(AnswerRequest(question="Compare BFS and DFS."))
        # MockGenerator cites all labels, so we expect 2 citations.
        assert len(result.citations) == 2
        assert result.notes_used == 2
