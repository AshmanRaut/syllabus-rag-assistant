"""tests/test_integration.py — Module D end-to-end integration tests.

These tests verify cross-module integration without requiring a running
Qdrant instance, LLM API key, or network access.  They use:
- MockGenerator for generation
- Inline fake retriever / web searcher
- Real SourceChunk / schema validation

Run:
    pytest tests/test_integration.py -v
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Sequence

import pytest

from course_qa.schemas import (
    AnswerRequest,
    AnswerResponse,
    CitationRecord,
    DiscoveredFile,
    IngestReport,
    RetrievedChunk,
    SourceChunk,
    WebSource,
)
from course_qa.generation import MockGenerator, create_generator
from course_qa.generation.citations import (
    build_labelled_evidence,
    retain_only_cited_sources,
)
from course_qa.service import QAService, should_search_web
from course_qa.config import settings


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_chunk(
    chunk_id: str = "int_c1",
    text: str = "Dijkstra's algorithm finds the shortest path in a weighted graph.",
    source_type: str = "typed_pdf",
    source_file: str = "aoa_notes/Typed/Dijkstra_Algorithm.pdf",
    subject: str = "AOA",
    page_number: int | None = 1,
    function_name: str | None = None,
    ocr_status: str = "not_needed",
) -> SourceChunk:
    return SourceChunk(
        chunk_id=chunk_id,
        source_id=f"src_{chunk_id}",
        subject=subject,  # type: ignore[arg-type]
        source_type=source_type,  # type: ignore[arg-type]
        source_file=source_file,
        page_number=page_number,
        function_name=function_name,
        text=text,
        content_hash=f"hash_{chunk_id}",
        source_hash=f"shash_{chunk_id}",
        ocr_status=ocr_status,  # type: ignore[arg-type]
    )


def _make_retrieved(score: float = 0.5, **kw) -> RetrievedChunk:
    return RetrievedChunk(chunk=_make_chunk(**kw), score=score, channel="hybrid")


def _make_web_source(
    source_id: str = "web_int1",
    snippet: str = "Dijkstra is used in GPS navigation.",
) -> WebSource:
    return WebSource(
        source_id=source_id,
        title="Dijkstra Applications",
        url="https://geeksforgeeks.org/dijkstra",
        domain="geeksforgeeks.org",
        snippet=snippet,
        retrieved_at="2026-10-26T00:00:00",
        text=snippet,
    )


class _FakeRetriever:
    """Deterministic retriever for integration tests."""

    def __init__(self, results: list[RetrievedChunk] | None = None):
        self._results = results or []
        self.calls: list[dict] = []

    def retrieve(
        self, question: str, *, subject: str | None = None, top_k: int = 5
    ) -> list[RetrievedChunk]:
        self.calls.append({"question": question, "subject": subject, "top_k": top_k})
        hits = self._results
        if subject and subject != "UNKNOWN":
            hits = [h for h in hits if h.chunk.subject == subject]
        return hits[:top_k]


class _FakeWebSearcher:
    """Deterministic web searcher for integration tests."""

    def __init__(
        self,
        results: list[WebSource] | None = None,
        raise_exc: Exception | None = None,
    ):
        self._results = results or []
        self._raise = raise_exc
        self.calls: list[str] = []

    def search(self, query: str, *, max_results: int = 5) -> list[WebSource]:
        self.calls.append(query)
        if self._raise:
            raise self._raise
        return self._results[:max_results]


def _build_mock_service(
    notes: list[RetrievedChunk] | None = None,
    web_results: list[WebSource] | None = None,
    web_exc: Exception | None = None,
) -> tuple[QAService, _FakeRetriever, _FakeWebSearcher]:
    retriever = _FakeRetriever(notes)
    searcher = _FakeWebSearcher(web_results, raise_exc=web_exc)
    generator = MockGenerator()
    svc = QAService(retriever, generator, searcher)
    return svc, retriever, searcher


# ===========================================================================
# Test class: Schema & contract compliance
# ===========================================================================


class TestSchemaCompliance:
    """Verify that all Pydantic models enforce the shared contract."""

    def test_source_chunk_rejects_unknown_fields(self):
        with pytest.raises(Exception):
            SourceChunk(
                chunk_id="x",
                source_id="x",
                subject="DS",
                source_type="code",
                source_file="f.c",
                text="t",
                content_hash="h",
                source_hash="h",
                bogus_field="should fail",
            )

    def test_answer_response_shape(self):
        resp = AnswerResponse(
            answer="test",
            citations=[],
            notes_used=0,
            web_used=0,
        )
        assert resp.abstained is False
        assert resp.warnings == []

    def test_discovered_file_valid_buckets(self):
        for bucket in ("typed", "handwritten", "code", "syllabus", "other"):
            df = DiscoveredFile(
                absolute_path="/a",
                relative_path="a",
                subject="DS",
                source_type="typed_pdf",
                bucket=bucket,
            )
            assert df.bucket == bucket

    def test_ingest_report_defaults(self):
        report = IngestReport()
        assert report.discovered == 0
        assert report.errors == []


# ===========================================================================
# Test class: Evidence labelling & citation pipeline
# ===========================================================================


class TestCitationPipeline:
    """End-to-end tests for evidence labelling → answer → citation validation."""

    def test_labelling_assigns_sequential_labels(self):
        notes = [
            _make_retrieved(chunk_id="a"),
            _make_retrieved(chunk_id="b"),
        ]
        context, records = build_labelled_evidence(notes, [])
        assert len(records) == 2
        assert records[0].label == "S1"
        assert records[1].label == "S2"
        assert "[S1]" in context
        assert "[S2]" in context

    def test_labelling_includes_web_after_notes(self):
        notes = [_make_retrieved(chunk_id="n1")]
        web = [_make_web_source()]
        context, records = build_labelled_evidence(notes, web)
        assert len(records) == 2
        assert records[0].source_kind != "web"
        assert records[1].source_kind == "web"
        assert records[1].label == "S2"

    def test_retain_strips_invalid_labels(self):
        records = [
            CitationRecord(
                label="S1",
                source_kind="note",
                source_file="f.pdf",
                source_id="s1",
            )
        ]
        answer = "According to [S1] and [S99], the answer is 42."
        cleaned, used, warnings = retain_only_cited_sources(answer, records)
        assert "[S99]" not in cleaned
        assert "[S1]" in cleaned
        assert len(used) == 1
        assert any("invalid" in w.lower() or "Removed" in w for w in warnings)

    def test_retain_warns_when_no_citations(self):
        records = [
            CitationRecord(
                label="S1",
                source_kind="note",
                source_file="f.pdf",
                source_id="s1",
            )
        ]
        answer = "The answer is 42."
        _, used, warnings = retain_only_cited_sources(answer, records)
        assert used == []
        assert any("no valid evidence" in w.lower() for w in warnings)

    def test_pending_ocr_chunks_excluded_from_evidence(self):
        notes = [
            _make_retrieved(chunk_id="pending", text="[pending OCR]", ocr_status="pending"),
            _make_retrieved(chunk_id="good", text="BFS uses a queue."),
        ]
        _, records = build_labelled_evidence(notes, [])
        labels = {r.source_id for r in records}
        assert "int_c1" not in labels or "pending" not in {r.source_id for r in records}
        # More specifically:
        record_ids = {r.source_id for r in records}
        assert "pending" not in record_ids


# ===========================================================================
# Test class: QAService end-to-end flows
# ===========================================================================


class TestServiceIntegration:
    """Full service pipeline: retrieve → route → generate → validate."""

    def test_notes_only_happy_path(self):
        notes = [
            _make_retrieved(chunk_id="dij1", text="Dijkstra finds shortest paths."),
            _make_retrieved(chunk_id="dij2", text="Time complexity is O(V^2).", source_file="aoa_notes/Typed/Dijkstra.pdf"),
        ]
        svc, retriever, searcher = _build_mock_service(notes=notes)
        result = svc.answer(
            AnswerRequest(question="Explain Dijkstra", subject="AOA", use_web=False)
        )

        assert isinstance(result, AnswerResponse)
        assert not result.abstained
        assert result.notes_used >= 1
        assert result.web_used == 0
        assert len(result.citations) >= 1
        assert searcher.calls == []  # Web should not have been called

    def test_notes_plus_web_path(self):
        notes = [_make_retrieved(chunk_id="bfs1", text="BFS uses a queue.", subject="DS")]
        web = [_make_web_source()]
        svc, retriever, searcher = _build_mock_service(notes=notes, web_results=web)
        result = svc.answer(
            AnswerRequest(
                question="Real-world applications of BFS?",
                subject="DS",
                use_web=True,
            )
        )

        assert isinstance(result, AnswerResponse)
        # Web was searched because of signal word "applications"
        assert len(searcher.calls) >= 1

    def test_abstention_when_no_evidence(self):
        svc, _, _ = _build_mock_service(notes=[], web_results=[])
        result = svc.answer(
            AnswerRequest(question="Unknown topic XYZ?", use_web=True)
        )
        assert result.abstained is True
        assert result.citations == []
        assert any("no" in w.lower() for w in result.warnings)

    def test_web_failure_graceful_degradation(self):
        notes = [_make_retrieved(chunk_id="ok", text="Linked lists are dynamic.")]
        svc, _, _ = _build_mock_service(
            notes=notes,
            web_exc=ConnectionError("DNS failed"),
        )
        result = svc.answer(
            AnswerRequest(
                question="Real-world applications of linked lists?",
                use_web=True,
            )
        )
        assert isinstance(result, AnswerResponse)
        assert any("Web search failed" in w for w in result.warnings)
        # Should still have note-based answer despite web failure
        assert result.notes_used >= 1

    def test_subject_filter_propagated(self):
        notes = [
            _make_retrieved(chunk_id="aoa1", text="Greedy approach.", subject="AOA"),
            _make_retrieved(chunk_id="ds1", text="Stack operations.", subject="DS"),
        ]
        svc, retriever, _ = _build_mock_service(notes=notes)
        svc.answer(
            AnswerRequest(question="Explain stacks", subject="DS", use_web=False)
        )
        assert retriever.calls[0]["subject"] == "DS"

    def test_web_toggle_off_strict_gate(self):
        """use_web=False must prevent any web call regardless of question content."""
        svc, _, searcher = _build_mock_service(
            notes=[_make_retrieved()],
            web_results=[_make_web_source()],
        )
        svc.answer(
            AnswerRequest(
                question="Real-world applications of Dijkstra?",
                use_web=False,
            )
        )
        assert searcher.calls == []

    def test_answer_style_concise(self):
        svc, _, _ = _build_mock_service(notes=[_make_retrieved()])
        result = svc.answer(
            AnswerRequest(question="What is BFS?", answer_style="concise")
        )
        assert isinstance(result, AnswerResponse)

    def test_multiple_citation_labels_in_answer(self):
        notes = [
            _make_retrieved(chunk_id="m1", text="BFS explores level by level."),
            _make_retrieved(chunk_id="m2", text="DFS uses backtracking."),
            _make_retrieved(chunk_id="m3", text="Both are graph traversal algorithms."),
        ]
        svc, _, _ = _build_mock_service(notes=notes)
        result = svc.answer(
            AnswerRequest(question="Compare BFS and DFS")
        )
        # MockGenerator cites all labels
        assert len(result.citations) == 3
        assert result.notes_used == 3


# ===========================================================================
# Test class: Web routing logic
# ===========================================================================


class TestWebRouting:
    """Verify should_search_web() follows the shared contract."""

    def test_use_web_false_always_returns_false(self):
        req = AnswerRequest(question="Anything", use_web=False)
        assert should_search_web(req, []) is False
        assert should_search_web(req, [_make_retrieved()]) is False

    def test_signal_word_triggers_web(self):
        req = AnswerRequest(question="Real-world applications of BFS?", use_web=True)
        assert should_search_web(req, [_make_retrieved(score=0.8)]) is True

    def test_empty_notes_trigger_web(self):
        req = AnswerRequest(question="What is BFS?", use_web=True)
        assert should_search_web(req, []) is True

    def test_weak_notes_trigger_web(self):
        req = AnswerRequest(question="What is BFS?", use_web=True)
        weak = [_make_retrieved(score=0.01)]
        assert should_search_web(req, weak) is True

    def test_strong_notes_no_signal_skips_web(self):
        req = AnswerRequest(question="What is BFS?", use_web=True)
        strong = [_make_retrieved(score=0.5)]
        assert should_search_web(req, strong) is False


# ===========================================================================
# Test class: create_generator() factory
# ===========================================================================


class TestGeneratorFactory:
    def test_returns_mock_when_no_llm_model(self, monkeypatch):
        import dataclasses
        import course_qa.generation.generator as gen_mod

        replacement = dataclasses.replace(gen_mod.settings, llm_model="")
        monkeypatch.setattr(gen_mod, "settings", replacement)
        g = create_generator()
        assert isinstance(g, MockGenerator)

    def test_returns_mock_on_init_failure(self, monkeypatch):
        import dataclasses
        import course_qa.generation.generator as gen_mod

        replacement = dataclasses.replace(gen_mod.settings, llm_model="some-model")
        monkeypatch.setattr(gen_mod, "settings", replacement)
        monkeypatch.setattr(gen_mod, "OpenAICompatibleGenerator", lambda: (_ for _ in ()).throw(RuntimeError("fail")))
        g = create_generator()
        assert isinstance(g, MockGenerator)


# ===========================================================================
# Test class: Evaluation questions file integrity
# ===========================================================================


class TestEvaluationQuestions:
    """Verify that the evaluation CSV is well-formed and covers required categories."""

    @pytest.fixture
    def questions_path(self) -> Path:
        return settings.chunks_jsonl.parent.parent / "evaluation" / "questions.csv"

    def test_csv_exists_and_has_rows(self, questions_path: Path):
        assert questions_path.exists(), f"Missing {questions_path}"
        with questions_path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert len(rows) >= 12, f"Expected ≥12 benchmark questions, got {len(rows)}"

    def test_csv_has_required_columns(self, questions_path: Path):
        with questions_path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            headers = set(reader.fieldnames or [])
        required = {"question_id", "question", "subject", "question_type"}
        assert required.issubset(headers), f"Missing columns: {required - headers}"

    def test_subjects_covered(self, questions_path: Path):
        with questions_path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            subjects = {row["subject"] for row in reader}
        assert "DS" in subjects, "No DS questions in evaluation set"
        assert "AOA" in subjects, "No AOA questions in evaluation set"

    def test_question_types_diverse(self, questions_path: Path):
        with questions_path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            types = {row["question_type"] for row in reader}
        assert len(types) >= 3, f"Expected ≥3 question types, got {types}"


# ===========================================================================
# Test class: Chunks JSONL integrity
# ===========================================================================


class TestChunksIntegrity:
    """Verify the canonical corpus is well-formed."""

    @pytest.fixture
    def chunks_path(self) -> Path:
        return settings.chunks_jsonl

    def test_chunks_file_exists(self, chunks_path: Path):
        assert chunks_path.exists(), f"Missing {chunks_path}"

    def test_chunks_are_valid_pydantic(self, chunks_path: Path):
        if not chunks_path.exists():
            pytest.skip("chunks.jsonl not found")
        errors = []
        count = 0
        for i, line in enumerate(chunks_path.read_text("utf-8").splitlines()):
            if not line.strip():
                continue
            try:
                SourceChunk.model_validate_json(line)
                count += 1
            except Exception as exc:
                errors.append(f"Line {i + 1}: {exc}")
        assert count > 0, "No valid chunks found"
        assert not errors, f"{len(errors)} invalid chunks:\n" + "\n".join(errors[:5])

    def test_no_duplicate_chunk_ids(self, chunks_path: Path):
        if not chunks_path.exists():
            pytest.skip("chunks.jsonl not found")
        ids: list[str] = []
        for line in chunks_path.read_text("utf-8").splitlines():
            if not line.strip():
                continue
            chunk = SourceChunk.model_validate_json(line)
            ids.append(chunk.chunk_id)
        assert len(ids) == len(set(ids)), f"Duplicate chunk_ids: {len(ids) - len(set(ids))} duplicates"

    def test_no_absolute_paths_in_source_file(self, chunks_path: Path):
        if not chunks_path.exists():
            pytest.skip("chunks.jsonl not found")
        for line in chunks_path.read_text("utf-8").splitlines():
            if not line.strip():
                continue
            chunk = SourceChunk.model_validate_json(line)
            assert not chunk.source_file.startswith("/"), (
                f"Absolute path in source_file: {chunk.source_file}"
            )

    def test_subjects_are_valid(self, chunks_path: Path):
        if not chunks_path.exists():
            pytest.skip("chunks.jsonl not found")
        valid = {"DS", "AOA", "UNKNOWN"}
        for line in chunks_path.read_text("utf-8").splitlines():
            if not line.strip():
                continue
            chunk = SourceChunk.model_validate_json(line)
            assert chunk.subject in valid, f"Invalid subject: {chunk.subject}"
