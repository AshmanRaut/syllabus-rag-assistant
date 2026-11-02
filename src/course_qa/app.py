"""src/course_qa/app.py — Clean, professional UI for Syllabus-Aware Course QA Assistant.

Focus: High usability, clean typography, minimalist engineering aesthetics,
and robust citation grounding for Data Structures & Analysis of Algorithms.
"""
from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Sequence

import gradio as gr

from .config import settings
from .schemas import AnswerRequest, AnswerResponse, Subject
from .service import QAService

logger = logging.getLogger(__name__)

# Professional, minimalist stylesheet (clean slate / monochrome / high readability)
CLEAN_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
    --bg-main: #090d16;
    --bg-card: #111827;
    --border-subtle: #1f2937;
    --border-strong: #374151;
    --text-main: #f3f4f6;
    --text-muted: #9ca3af;
    --accent: #2563eb;
    --accent-hover: #1d4ed8;
}

body, .gradio-container {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    background-color: var(--bg-main) !important;
    color: var(--text-main) !important;
}

code, pre {
    font-family: 'JetBrains Mono', monospace !important;
}

/* Header container */
.app-header {
    border-bottom: 1px solid var(--border-subtle);
    padding: 16px 0 20px 0;
    margin-bottom: 20px;
}

.app-title {
    font-size: 1.5rem !important;
    font-weight: 700 !important;
    color: #f9fafb !important;
    margin: 0 0 6px 0 !important;
}

.app-subtitle {
    font-size: 0.92rem !important;
    color: var(--text-muted) !important;
    margin: 0 !important;
}

/* Completely hide Gradio default footer bar and all branding */
footer,
.footer,
.gradio-container footer,
.gradio-container > footer,
div[class*="footer"] {
    display: none !important;
    visibility: hidden !important;
    opacity: 0 !important;
    height: 0 !important;
    padding: 0 !important;
    margin: 0 !important;
    pointer-events: none !important;
}

/* Panel cards */
.panel-card {
    background: var(--bg-card) !important;
    border: 1px solid var(--border-subtle) !important;
    border-radius: 8px !important;
    padding: 18px !important;
}

/* Action button */
.primary-btn {
    background-color: var(--accent) !important;
    color: #ffffff !important;
    font-weight: 600 !important;
    border-radius: 6px !important;
    border: none !important;
    padding: 10px 18px !important;
    transition: background-color 0.15s ease !important;
}

.primary-btn:hover {
    background-color: var(--accent-hover) !important;
}

/* Example chips */
.sample-chip {
    font-size: 0.8rem !important;
    padding: 4px 10px !important;
    border-radius: 4px !important;
    background: #1f2937 !important;
    border: 1px solid #374151 !important;
    color: #d1d5db !important;
    text-align: left !important;
}

.sample-chip:hover {
    background: #374151 !important;
    color: #ffffff !important;
}

/* Output answer */
.answer-content {
    background: #0f172a !important;
    border: 1px solid #1e293b !important;
    border-radius: 6px !important;
    padding: 20px !important;
    font-size: 0.96rem !important;
    line-height: 1.65 !important;
}
"""


def build_service() -> QAService:
    """Build QAService with resilient boot defaults."""
    warnings: list[str] = []

    # 1. Chunks
    from .retrieval.hybrid import HybridRetriever, load_chunks

    chunks = load_chunks()
    if not chunks:
        raise RuntimeError(
            "No chunks indexed yet. Run scripts/ingest.py and scripts/index.py first."
        )
    logger.info("Loaded %d chunks from %s", len(chunks), settings.chunks_jsonl)

    # 2. Embedder
    from .retrieval.embedder import SentenceTransformerEmbedder

    embedder = SentenceTransformerEmbedder(settings.embedding_model)

    # 3. Store
    from .retrieval.qdrant_store import QdrantDenseStore

    store = QdrantDenseStore(embedder.dimension)

    # 4. Retriever
    retriever = HybridRetriever(chunks, embedder, store)

    # 5. Generator
    from .generation import create_generator

    generator = create_generator()
    gen_name = type(generator).__name__
    if gen_name == "MockGenerator":
        warnings.append(
            "Running with MockGenerator (LLM_MODEL is unset). Evidence is retrieved and cited."
        )

    # 6. Web Search
    from .web.search import WebSearch

    web = WebSearch()

    service = QAService(retriever, generator, web)
    service._boot_warnings = warnings
    service._chunks_count = len(chunks)
    service._embedder_dim = embedder.dimension
    return service


def build_ui(service: QAService | None = None) -> gr.Blocks:
    """Build clean, professional Gradio interface."""
    if service is None:
        service = build_service()

    boot_warnings: list[str] = getattr(service, "_boot_warnings", [])

    def respond(
        question: str, subject: str, use_web: bool, style: str
    ) -> tuple[str, list, str, list, str]:
        t0 = time.perf_counter()
        if not question or not question.strip():
            return (
                "Please enter a question or select one of the benchmark samples below.",
                [],
                "No query submitted.",
                [],
                "Elapsed: 0.0s",
            )

        req_subject = None if subject == "Any" else subject
        request = AnswerRequest(
            question=question.strip(),
            subject=req_subject,
            use_web=bool(use_web),
            answer_style=style,
        )

        try:
            response: AnswerResponse = service.answer(request)
        except Exception as exc:
            logger.exception("QAService.answer() execution error")
            return (
                f"### Execution Error\n\n`{type(exc).__name__}: {exc}`",
                [],
                f"Error: {exc}",
                [],
                f"Elapsed: {time.perf_counter() - t0:.2f}s",
            )

        elapsed = time.perf_counter() - t0

        # Sources table
        source_rows: list[list[str]] = []
        for c in response.citations:
            loc = c.source_file or c.url or c.title or c.source_id
            if c.page_number is not None:
                loc += f" (Page {c.page_number})"
            if c.function_name:
                loc += f" -> {c.function_name}()"
            source_rows.append([
                f"[{c.label}]",
                c.source_kind.upper(),
                c.title or (Path(c.source_file).name if c.source_file else "Web Source"),
                loc,
                c.url or "—",
                c.image_path or "—",
            ])

        # Page images gallery
        images = []
        for c in response.citations:
            if c.image_path:
                img_p = Path(c.image_path)
                if img_p.exists():
                    images.append((str(img_p), f"[{c.label}] {c.title or img_p.name}"))

        # Warnings
        all_warnings = boot_warnings + response.warnings
        if response.abstained:
            all_warnings.append("System abstained: insufficient grounding evidence in notes.")

        warnings_md = "\n".join(f"- {w}" for w in all_warnings) if all_warnings else "No warnings. Grounding checks passed."

        # Header summary
        summary_tags = []
        if response.notes_used:
            summary_tags.append(f"{response.notes_used} note source(s)")
        if response.web_used:
            summary_tags.append(f"{response.web_used} web source(s)")
        if response.abstained:
            summary_tags.append("Abstained (insufficient evidence)")
        summary_tags.append(f"{elapsed:.2f}s latency")

        header_text = " · ".join(summary_tags)
        if response.abstained:
            full_answer = (
                f"**Status:** {header_text}\n\n---\n\n"
                f"> ⚠️ **Abstained — Insufficient Grounding Evidence**\n>\n"
                f"> {response.answer}\n"
            )
        else:
            full_answer = f"**Status:** {header_text}\n\n---\n\n{response.answer}"

        if not use_web:
            web_status = "Disabled (toggle off)"
        elif response.web_used > 0:
            web_status = f"Active ({response.web_used} web source(s) cited)"
        else:
            web_status = "Bypassed (course notes sufficient; no external signal)"

        telemetry = (
            f"- Latency: `{elapsed:.3f}s`\n"
            f"- Subject: `{subject}`\n"
            f"- Style: `{style}`\n"
            f"- Web Search: `{web_status}`\n"
            f"- Notes Used: `{response.notes_used}`\n"
            f"- Web Used: `{response.web_used}`\n"
            f"- Abstained: `{response.abstained}`\n"
        )

        return full_answer, source_rows, warnings_md, images, telemetry

    # ── UI Construction ──────────────────────────────────────────────────
    with gr.Blocks(title="Course QA Assistant") as demo:
        # Minimalist Header
        with gr.Column(elem_classes=["app-header"]):
            gr.Markdown(
                """
                # Syllabus-Aware Course QA Assistant
                Source-grounded question answering for **Data Structures** and **Analysis of Algorithms**.
                """
            )

        with gr.Row():
            # Left Column: Inputs
            with gr.Column(scale=5, elem_classes=["panel-card"]):
                gr.Markdown("### Question")
                q = gr.Textbox(
                    label="Query",
                    lines=3,
                    placeholder="Enter an algorithm theory, code, or complexity question...",
                    show_label=False,
                )

                gr.Markdown("##### Sample Benchmarks:")
                with gr.Row():
                    b1 = gr.Button("Fractional Knapsack (AOA)", size="sm", elem_classes=["sample-chip"])
                    b2 = gr.Button("Dijkstra Relaxation (Code)", size="sm", elem_classes=["sample-chip"])
                    b3 = gr.Button("Reverse Linked List (DS)", size="sm", elem_classes=["sample-chip"])
                with gr.Row():
                    b4 = gr.Button("AVL Rotations (Notes)", size="sm", elem_classes=["sample-chip"])
                    b5 = gr.Button("Dijkstra Applications (Web)", size="sm", elem_classes=["sample-chip"])
                    b6 = gr.Button("Out-of-Corpus Query (Abstain)", size="sm", elem_classes=["sample-chip"])

                with gr.Row():
                    subject = gr.Dropdown(
                        choices=["Any", "DS", "AOA"],
                        value="Any",
                        label="Subject Filter",
                    )
                    style = gr.Radio(
                        choices=["exam", "concise"],
                        value="exam",
                        label="Answer Style",
                    )

                use_web = gr.Checkbox(
                    value=False,
                    label="Enable Web Search Augmentation",
                    info="Strict permission gate: searches allowlisted domains only when checked",
                )

                with gr.Row():
                    submit = gr.Button("Submit Question", variant="primary", elem_classes=["primary-btn"], scale=3)
                    clear_btn = gr.Button("Clear", variant="secondary", scale=1)

            # Right Column: Output Tabs
            with gr.Column(scale=7, elem_classes=["panel-card"]):
                with gr.Tabs():
                    with gr.TabItem("Answer"):
                        answer_box = gr.Markdown(
                            value="*Answer will appear here after submission.*",
                            elem_classes=["answer-content"],
                        )

                    with gr.TabItem("Sources"):
                        sources_table = gr.Dataframe(
                            headers=["Citation", "Kind", "Title", "Location", "URL", "Page Image"],
                            interactive=False,
                            wrap=True,
                        )

                    with gr.TabItem("Page Scans"):
                        gallery = gr.Gallery(
                            label="Cited PDF Page Images",
                            columns=2,
                            rows=2,
                            height=480,
                            object_fit="contain",
                        )

                    with gr.TabItem("Diagnostics"):
                        gr.Markdown("#### Execution Telemetry")
                        telemetry_box = gr.Markdown(value="*No query executed yet.*")
                        gr.Markdown("#### System Warnings")
                        warnings_box = gr.Markdown(value="*No active warnings.*")

        # Handlers
        submit.click(
            respond,
            inputs=[q, subject, use_web, style],
            outputs=[answer_box, sources_table, warnings_box, gallery, telemetry_box],
        )

        q.submit(
            respond,
            inputs=[q, subject, use_web, style],
            outputs=[answer_box, sources_table, warnings_box, gallery, telemetry_box],
        )

        clear_btn.click(
            lambda: ("", "Any", False, "exam", "*Ready.*", [], "No warnings.", [], "*No query executed yet.*"),
            inputs=[],
            outputs=[q, subject, use_web, style, answer_box, sources_table, warnings_box, gallery, telemetry_box],
        )

        # Sample chip bindings
        b1.click(
            lambda: ("Define the fractional knapsack problem and explain its greedy choice criterion.", "AOA", False),
            inputs=[],
            outputs=[q, subject, use_web],
        )
        b2.click(
            lambda: ("Trace the core relaxation loop in dijkstra() from the supplied C code.", "AOA", False),
            inputs=[],
            outputs=[q, subject, use_web],
        )
        b3.click(
            lambda: ("Explain how reverse() reverses the linked list using three pointers in LinkedList6p.c.", "DS", False),
            inputs=[],
            outputs=[q, subject, use_web],
        )
        b4.click(
            lambda: ("Explain AVL tree rotations and balance factor invariants from course notes.", "DS", False),
            inputs=[],
            outputs=[q, subject, use_web],
        )
        b5.click(
            lambda: ("Give real-world practical applications of Dijkstra algorithm in computer networks.", "AOA", True),
            inputs=[],
            outputs=[q, subject, use_web],
        )
        b6.click(
            lambda: ("What exact grading rubric did my instructor privately use for this class?", "Any", False),
            inputs=[],
            outputs=[q, subject, use_web],
        )

    return demo


def main() -> None:
    demo = build_ui()
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        show_error=True,
        footer_links=[],
        run_history=False,
        theme=gr.themes.Base(),
        css=CLEAN_CSS,
    )


if __name__ == "__main__":
    main()
