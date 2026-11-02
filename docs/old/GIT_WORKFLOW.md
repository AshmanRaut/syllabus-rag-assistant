# One-day Git workflow

## Shared base
1. One person creates the GitHub repository from this scaffold and pushes the contract commit first.
2. Everyone pulls `main` and reads `docs/SHARED_CONTRACT.md`.
3. Agree on `.env.example`, schema field names and public function signatures before working in parallel.

## Branches and file ownership

- `feat/ingestion-ocr` — Person A: ingestion files, scanner/ingest scripts, ingestion tests.
- `feat/qdrant-hybrid-web` — Person B: retrieval, Qdrant, BM25/RRF, web module, index script.
- `feat/generation-citations` — Person C: router, generator adapters, citation formatter, service tests.
- `feat/ui-evaluation` — Person D: Gradio UI, integration/evaluation tests, demo/report.

Avoid editing each other's files. If a schema change is unavoidable, open a short shared contract change before adapting all modules.

## Merge rules
- Small, focused commits.
- `pytest -q` passes before merge or the failing test is explained and tracked.
- Merge ingestion schemas before module integration; merge core retrieval and generator before app wiring.
- Integrator pulls and smoke-tests after each merge.
- Keep `main` runnable; do not merge API keys, real course content, page images, OCR caches or indexes.
