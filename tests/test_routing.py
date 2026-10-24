from course_qa.schemas import AnswerRequest
from course_qa.service import should_search_web

def test_web_checkbox_is_permission_gate():
    assert should_search_web(AnswerRequest(question="What is Dijkstra?", use_web=False), []) is False

def test_web_enabled_routes_when_notes_are_missing():
    assert should_search_web(AnswerRequest(question="Explain this topic", use_web=True), []) is True

def test_web_enabled_routes_for_explicit_external_applications():
    assert should_search_web(AnswerRequest(question="Give real-world applications of Dijkstra", use_web=True), []) is True
