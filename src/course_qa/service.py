from __future__ import annotations

import logging
from .schemas import AnswerRequest, AnswerResponse
from .config import settings

logger = logging.getLogger(__name__)

WEB_SIGNAL_WORDS = (
    "real-world application",
    "real world",
    "real-world",
    "applications",
    "application",
    "compare",
    "comparison",
    "versus",
    "vs",
    "latest",
    "recent",
    "current",
    "modern",
    "industry use",
    "industry",
    "practical use",
    "practical",
    "external",
    "web",
    "online",
)


def should_search_web(request: AnswerRequest, notes: list) -> bool:
    """Determine whether the web searcher should be called for this request.

    The ``use_web`` flag is a strict **permission gate**: if it is False the
    function returns False unconditionally, regardless of note coverage.

    When ``use_web`` is True the function calls web if:
    - The question contains signal words that imply a need for external context
      (real-world applications, comparisons, etc.), OR
    - Notes are absent or their top RRF score is very weak (< 0.025).

    The global ``WEB_SEARCH_MODE`` setting can disable web unconditionally when
    set to ``"off"``.
    """
    if settings.web_search_mode.lower() == "off" or not request.use_web:
        return False
    q = request.question.lower()
    if any(phrase in q for phrase in WEB_SIGNAL_WORDS):
        return True
    # RRF scores are rank-fusion values, not calibrated probabilities.
    # Fall back to web when there is no note evidence or the top score is very low.
    return not notes or (notes[0].score < 0.025)


class QAService:
    """Orchestrates retrieval → web fallback → generation for a single question.

    Dependencies are injected via the constructor so the service works with any
    implementation that satisfies the ``NotesRetriever``, ``AnswerGenerator``,
    and ``WebSearcher`` protocols defined in ``contracts.py``.
    """

    def __init__(self, notes_retriever, generator, web_searcher) -> None:
        self.notes_retriever = notes_retriever
        self.generator = generator
        self.web_searcher = web_searcher

    def answer(self, request: AnswerRequest) -> AnswerResponse:
        # --- 1. Retrieve from notes index -----------------------------------
        notes = self.notes_retriever.retrieve(
            request.question,
            subject=request.subject,
            top_k=settings.hybrid_top_k,
        )

        # --- 2. Conditionally call web search --------------------------------
        web: list = []
        web_warning: str | None = None
        if should_search_web(request, notes):
            try:
                web = self.web_searcher.search(request.question)
            except Exception as exc:
                web = []
                web_warning = f"Web search failed: {type(exc).__name__}: {exc}"
                logger.warning(web_warning)

        # --- 3. Generate answer ---------------------------------------------
        result = self.generator.generate(request, notes, web)

        # --- 4. Post-process: attach web-search failure warning --------------
        if web_warning:
            result.warnings.append(web_warning)

        # --- 5. Force abstention when absolutely no evidence was available ---
        if not notes and not web:
            result.abstained = True
            if not any("No evidence" in w or "no evidence" in w for w in result.warnings):
                result.warnings.append(
                    "No note or web evidence was available. "
                    "The response should not be treated as grounded."
                )

        return result
