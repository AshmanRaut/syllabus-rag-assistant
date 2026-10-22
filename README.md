# Syllabus-Aware DS/AoA NLP Assistant

A one-day NLP mini-project: retrieve evidence from course notes and C lab code, optionally supplement it with web search, and generate exam-style answers with validated source references.

## Project constraints

- Four contributors, one build day.
- Preserve Qdrant in the retrieval stack.
- Notes-first deterministic routing; web search is retained as an explicit toggle and a fallback for weak/missing note evidence or questions that benefit from external sources.
- Handwritten page OCR must be cached by content hash and resumable.
- No fine-tuning, OCR training, diagram caption generation, or image-only retrieval in the MVP.

## Repository setup

```bash
python -m venv .venv
source .venv/bin/activate           # Windows: .venv\\Scripts\\activate
python -m pip install --upgrade pip
pip install -e . -r requirements.txt -r requirements-web.txt
cp .env.example .env
```

Put your course material under a root directory matching this layout, or set `SOURCE_ROOT` to the directory containing these subfolders:

```text
<source-root>/
├── AOA codes/
├── AOA notes/
│   ├── Typed/
│   └── Handwritten/
├── DS codes/
├── DS notes/
│   ├── Typed/
│   └── Handwritten/
└── syllabi/                         # optional: AOA_Syllabus.pdf, DS_Syllabus.pdf
```

The scanner also supports PDF, common image files, `.c`, `.h`, `.txt`, and `.md`. Never commit the real course notes, `.env`, credentials, page images, or generated indexes.

## Start Qdrant

```bash
docker compose up -d qdrant
```

The app can also use Qdrant's persistent local client by leaving `QDRANT_URL` blank. Docker is the recommended shared team setup so every contributor uses the same API shape.

## First milestones

1. `python scripts/scan_sources.py` — inspect how many files are discovered and whether their categories are correct.
2. Implement/test ingestion and create `data/processed/chunks.jsonl`.
3. Embed and upsert chunks to Qdrant; build the BM25 index; run hybrid retrieval tests.
4. Plug retrieval into generator, web fallback, citation formatter, then Gradio UI.
5. Start from `data/evaluation/questions.csv`, fill in actual chunk IDs after indexing, and record failures before the demo.

## Optional dependencies

- `pip install -r requirements-web.txt` enables Tavily/DDGS providers. Add `TAVILY_API_KEY` for Tavily; otherwise DDGS is best-effort and can be throttled.
- `requirements-docling.txt` is only needed if native typed-PDF extraction is poor.
- `requirements-ocr.txt` is optional; test PaddleOCR-VL in an isolated environment first. Configure `OCR_PROVIDER=paddleocr_vl` only after a smoke test. `OCR_MAX_PAGES=5` is the pilot default; set it to `0` for unlimited uncached pages after checking quality.

## Environment

Copy `.env.example` to `.env`. The app must work with web search disabled and without an OCR provider. The generator uses an adapter interface: configure an OpenAI-compatible endpoint, or implement a provider adapter for the model/API you have access to. Having Claude Opus in Antigravity does not by itself imply API credentials for the app.

## Shared contracts and ownership

Read `docs/SHARED_CONTRACT.md` before parallel implementation. Read `docs/BUILD_PLAN.md` for the full plan and `docs/CLAUDE_ORCHESTRATION_PROMPT.md` to orchestrate the work with Claude Opus.

## Useful commands (to be implemented by the assigned owners)

```bash
python scripts/scan_sources.py
python scripts/ingest.py --resume --max-ocr-pages 5
python scripts/index.py
python -m course_qa.app
pytest -q
```

The starter is a contract-first scaffold, not a claim that every adapter is already production-ready. The implementation checklist in the build plan identifies which module owns each command and what counts as done.
