from course_qa.schemas import AnswerRequest
from course_qa.service import should_search_web

def test_web_checkbox_is_permission_gate():
    assert should_search_web(AnswerRequest(question="What is Dijkstra?", use_web=False), []) is False

def test_web_enabled_routes_when_notes_are_missing():
    assert should_search_web(AnswerRequest(question="Explain this topic", use_web=True), []) is True

def test_web_enabled_routes_for_explicit_external_applications():
    assert should_search_web(AnswerRequest(question="Give real-world applications of Dijkstra", use_web=True), []) is True

def test_web_not_used_when_notes_are_strong():
    from course_qa.schemas import SourceChunk, RetrievedChunk
    chunk = SourceChunk(
        chunk_id="c1",
        source_id="s1",
        subject="AOA",
        source_type="typed_pdf",
        source_file="test.pdf",
        text="test",
        content_hash="h",
        source_hash="s",
    )
    strong_notes = [RetrievedChunk(chunk=chunk, score=0.5, channel="hybrid", rank=1)]
    assert should_search_web(
        AnswerRequest(question="Explain Dijkstra", use_web=True), strong_notes
    ) is False
