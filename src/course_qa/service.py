from __future__ import annotations
from .schemas import AnswerRequest, AnswerResponse
from .config import settings

WEB_SIGNAL_WORDS = ("real-world application", "applications", "compare", "comparison", "latest", "current", "industry use", "practical use")

def should_search_web(request: AnswerRequest, notes) -> bool:
    if settings.web_search_mode.lower() == "off" or not request.use_web:
        return False  # unchecked UI toggle is strict notes-only mode
    q = request.question.lower()
    if any(phrase in q for phrase in WEB_SIGNAL_WORDS): return True
    # RRF top scores are rank-fusion values rather than probability estimates. This is a routing heuristic,
    # not a calibrated confidence score. Use web fallback for missing/very weak note evidence.
    return not notes or (notes[0].score < 0.025)

class QAService:
    def __init__(self, notes_retriever, generator, web_searcher):
        self.notes_retriever = notes_retriever
        self.generator = generator
        self.web_searcher = web_searcher

    def answer(self, request: AnswerRequest) -> AnswerResponse:
        notes = self.notes_retriever.retrieve(request.question, subject=request.subject, top_k=settings.hybrid_top_k)
        web = []
        if should_search_web(request, notes):
            try: web = self.web_searcher.search(request.question)
            except Exception as exc:
                web = []
                web_warning = f"Web search failed: {type(exc).__name__}: {exc}"
            else: web_warning = None
        else:
            web_warning = None
        result = self.generator.generate(request, notes, web)
        if web_warning: result.warnings.append(web_warning)
        if not notes and not web:
            result.abstained = True
            result.warnings.append("No note or web evidence was available. The response should not be treated as grounded.")
        return result
