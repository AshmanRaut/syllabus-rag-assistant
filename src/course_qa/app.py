from __future__ import annotations
from pathlib import Path
import gradio as gr
from .config import settings
from .schemas import AnswerRequest
from .retrieval.hybrid import load_chunks, HybridRetriever
from .retrieval.embedder import SentenceTransformerEmbedder
from .retrieval.qdrant_store import QdrantDenseStore
from .generation.generator import OpenAICompatibleGenerator
from .web.search import WebSearch
from .service import QAService

def build_service():
    chunks = load_chunks()
    if not chunks:
        raise RuntimeError("No chunks indexed yet. Run ingestion and index scripts first.")
    embedder = SentenceTransformerEmbedder(settings.embedding_model)
    store = QdrantDenseStore(embedder.dimension)
    return QAService(HybridRetriever(chunks, embedder, store), OpenAICompatibleGenerator(), WebSearch())

def main():
    service = build_service()
    def respond(question, subject, use_web, style):
        if not question or not question.strip(): return "Enter a question.", [], ""
        request = AnswerRequest(question=question.strip(), subject=None if subject == "Any" else subject,
            use_web=bool(use_web), answer_style=style)
        response = service.answer(request)
        source_rows = []
        for c in response.citations:
            locator = c.source_file or c.url or c.title or c.source_id
            if c.page_number is not None: locator += f" · page {c.page_number}"
            if c.function_name: locator += f" · {c.function_name}()"
            source_rows.append([f"[{c.label}]", c.source_kind, c.title or "", locator, c.url or "", c.image_path or ""])
        warnings = "\n".join(response.warnings) if response.warnings else "No warnings."
        images = [str(Path(c.image_path)) for c in response.citations if c.image_path and Path(c.image_path).exists()]
        return response.answer, source_rows, warnings, images
    with gr.Blocks(title="DS/AoA NLP Assistant") as demo:
        gr.Markdown("# DS/AoA Exam Assistant\nAnswers are grounded in your notes and code. Web evidence is labelled separately.")
        q = gr.Textbox(label="Question", lines=3, placeholder="Explain Dijkstra's algorithm and its complexity")
        with gr.Row():
            subject = gr.Dropdown(["Any", "DS", "AOA"], value="Any", label="Subject")
            style = gr.Radio(["exam", "concise"], value="exam", label="Answer style")
            use_web = gr.Checkbox(value=False, label="Enable web search (off = notes only)")
        submit = gr.Button("Answer", variant="primary")
        answer = gr.Markdown()
        sources = gr.Dataframe(headers=["Citation", "Kind", "Title", "Location", "URL", "Page image path"], interactive=False)
        warnings = gr.Markdown()
        images = gr.Gallery(label="Original cited page images", columns=3, height="auto")
        submit.click(respond, [q, subject, use_web, style], [answer, sources, warnings, images])
    demo.launch()

if __name__ == "__main__": main()
