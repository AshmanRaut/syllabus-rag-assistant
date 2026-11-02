# Syllabus-Aware Course QA Assistant

[![Tests](https://img.shields.io/badge/tests-106%20passed-brightgreen.svg)](#testing)
[![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12-blue.svg)](#prerequisites)
[![Retrieval](https://img.shields.io/badge/retrieval-Qdrant%20%2B%20BM25%20(RRF)-orange.svg)](#architecture)
[![License](https://img.shields.io/badge/license-MIT-lightgrey.svg)](LICENSE)

A source-grounded academic question answering system tailored for undergraduate **Data Structures (DS)** and **Analysis of Algorithms (AOA)**. The assistant retrieves evidence from lecture slides, typed PDFs, and C lab implementations, supplements out-of-corpus queries via allowlisted web search, and produces exam-ready answers with strict source verification and visual slide citations.

---

## Key Capabilities

- **Hybrid Dense-Sparse Retrieval:** Combines semantic vector search (Qdrant with `all-MiniLM-L6-v2`) and lexical search (Okapi BM25) fused via Reciprocal Rank Fusion (RRF).
- **Strict Grounding & Citation Validation:** Automatically strips ungrounded claims; enforces verified inline `[S1]`, `[S2]` citation tags.
- **Honest Abstention:** If no relevant course evidence is found, the system cleanly abstains rather than fabricating answers from general training data.
- **Visual Slide Scans:** Renders 150 DPI page scans of cited lecture notes directly inside the UI gallery for visual proof.
- **Full C Code Synthesis:** Supports complete, compilable C programs for algorithms (Dijkstra, Floyd-Warshall, LCS, Knapsack, etc.) without truncation.
- **Zero-Key Offline Fallback:** Includes a deterministic `MockGenerator` for automated testing and offline evaluation without API keys.
- **Flexible LLM Backends:** Official OpenAI-compatible adapter supporting Google Gemini (Flash 3.5), Groq Cloud (`qwen3.8-27b`), Local Ollama (`llama3.2`), and OpenAI (`gpt-4o-mini`).

---

## Architecture Overview

```
                               ┌─────────────────────────────┐
                               │     User Query (Gradio)     │
                               └──────────────┬──────────────┘
                                              │
                      ┌───────────────────────┴───────────────────────┐
                      ▼                                               ▼
         ┌─────────────────────────┐                     ┌─────────────────────────┐
         │ Qdrant Dense Vector     │                     │     Okapi BM25 Index    │
         │ (all-MiniLM-L6-v2)      │                     │     (Lexical Search)    │
         └────────────┬────────────┘                     └────────────┬────────────┘
                      │                                               │
                      └───────────────────────┬───────────────────────┘
                                              ▼
                               ┌─────────────────────────────┐
                               │ Reciprocal Rank Fusion (RRF)│
                               └──────────────┬──────────────┘
                                              │
                    ┌─────────────────────────┴─────────────────────────┐
                    │ (Optional) Web Search (DDGS / Tavily Allowlist)   │
                    └─────────────────────────┬─────────────────────────┘
                                              ▼
                               ┌─────────────────────────────┐
                               │ Evidence Formatter ([S1]...)│
                               └──────────────┬──────────────┘
                                              │
                                              ▼
                               ┌─────────────────────────────┐
                               │   LLM Generator (Gemini/    │
                               │   Groq/Ollama/Mock)         │
                               └──────────────┬──────────────┘
                                              │
                                              ▼
                               ┌─────────────────────────────┐
                               │ Citation Validator & Filter │
                               └──────────────┬──────────────┘
                                              │
                                              ▼
                               ┌─────────────────────────────┐
                               │  UI: Answer + Sources Table │
                               │  + Cited Slide Images       │
                               └─────────────────────────────┘
```

---

## Quick Start (Run Locally)

### Prerequisites

- **Python:** Version 3.11 or 3.12 (Python 3.12 recommended).
- **Operating System:** macOS, Linux, or Windows (WSL2).

---

### Step 1: Clone & Create Virtual Environment

```bash
# Clone the repository
git clone https://github.com/AshmanRaut/syllabus-rag-assistant.git
cd syllabus-rag-assistant

# Create a clean virtual environment
python3.12 -m venv .venv
source .venv/bin/activate       # On Windows: .venv\Scripts\activate

# Upgrade pip
python -m pip install --upgrade pip
```

---

### Step 2: Install Dependencies

```bash
# Install core and web search dependencies in editable mode
pip install -e . -r requirements.txt -r requirements-web.txt
```

---

### Step 3: Configure Environment (`.env`)

Copy the example configuration:
```bash
cp .env.example .env
```

Open `.env` and configure your preferred LLM provider:

#### Option A: Google Gemini (Recommended — 1,000,000 TPM, Free Tier)
Get a free API key at **[Google AI Studio](https://aistudio.google.com/app/apikey)**:
```env
LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
LLM_API_KEY=AIzaSy...your_gemini_key_here...
LLM_MODEL=gemini-3.5-flash
LLM_TEMPERATURE=0.1
LLM_MAX_TOKENS=8192
```

#### Option B: Local Offline with Ollama (100% Free, Zero Internet)
```env
LLM_BASE_URL=http://localhost:11434/v1
LLM_API_KEY=ollama
LLM_MODEL=llama3.2
LLM_MAX_TOKENS=4096
```

#### Option C: Offline Deterministic Mock (Zero Keys Needed)
Leave `LLM_MODEL=` empty. The app will boot with real hybrid retrieval and verified citations without making external API calls.

> [!TIP]
> For a detailed walkthrough of all 24 environment settings, read [`docs/ENV_SETUP_GUIDE.md`](docs/ENV_SETUP_GUIDE.md).

---

### Step 4: Launch the Assistant

Launch the interactive Gradio web application:
```bash
python run.py
```

Open your browser at:
👉 **`http://localhost:7860`**

---

## Interactive UI Features

The Gradio web interface provides a dedicated multi-tab view:

1. **Answer Tab:**
   - Displays the synthesized answer with inline citation tags (e.g. `[S1]`, `[S2]`).
   - Supports two styles:
     - **Exam Style:** Structured university exam format with (1) Definition, (2) Algorithm steps, (3) Dry run / example, (4) Full C code, (5) Complexity, (6) Applications.
     - **Concise Style:** Compact 1–2 paragraph direct answers.
2. **Sources Tab:**
   - Detailed evidence table displaying: Citation Label, Source Kind (`NOTE`, `CODE`, `WEB`), Title, Physical Location (File, Page, Function), and URLs.
3. **Page Scans Tab:**
   - Interactive high-resolution gallery showing the exact PDF slide pages cited in the answer.
4. **Diagnostics Tab:**
   - Real-time telemetry: query execution latency, active subject filter, notes vs. web sources cited, and web routing status.

---

## Ingestion & Indexing Pipeline

Pre-computed index files are provided out of the box in the repository. To re-scan or index your own course materials:

```bash
# 1. Scan course notes directory (notes/)
python scripts/scan_sources.py

# 2. Ingest notes, extract text, parse C code, and render slide scans
python scripts/ingest.py --resume

# 3. Build lexical BM25 index and upsert dense vectors to Qdrant
python scripts/index.py --rebuild
```

> [!NOTE]
> **Qdrant Storage Lock:** The local embedded Qdrant instance locks `.data/qdrant` during execution. If you rebuild the index (`python scripts/index.py --rebuild`), stop `python run.py` first with `Ctrl+C`.

---

## Testing & Verification

The test suite covers unit contracts, hybrid retrieval, reciprocal rank fusion, web allowlisting, citation retention, and end-to-end routing.

```bash
# Run all 106 automated tests
pytest -q
```

### Benchmark Evaluation (15 Questions)

Run the standardized benchmark suite across 15 syllabus and out-of-corpus queries:
```bash
python scripts/evaluate.py
```

Benchmark evaluation verifies:
- Theory retrieval across typed PDFs.
- C code function extraction and AST parsing.
- Out-of-corpus query abstention (rubric / grading questions).
- Web search augmentation with educational domain allowlists.

---

## Repository Structure

```text
syllabus-rag-assistant/
├── .env.example                     # Environment template with provider recipes
├── pyproject.toml                   # Project configuration and dependencies
├── run.py                           # Application entrypoint
├── notes/                           # Course materials (PDFs, slides, C code)
├── data/
│   ├── evaluation/questions.csv     # 15 benchmark evaluation questions
│   ├── index/bm25.json              # Serialized BM25 lexical index
│   └── page_images/                 # Rendered 150 DPI PDF slide images
├── docs/
│   ├── ENV_SETUP_GUIDE.md           # Exhaustive .env configuration guide
│   ├── SHARED_CONTRACT.md           # Inter-module protocols and data schemas
│   ├── INTEGRATION_CHECKLIST.md     # Production release checklist
│   ├── EVALUATION.md                # Benchmark results and metrics
│   └── DEMO_SCRIPT.md               # 3-minute evaluation demo script
├── scripts/
│   ├── scan_sources.py              # Discovers and categorizes course files
│   ├── ingest.py                    # Chunks PDFs and C code with OCR cache
│   ├── index.py                     # Indexes chunks into Qdrant & BM25
│   └── evaluate.py                  # Runs 15-question benchmark evaluation
├── src/course_qa/
│   ├── app.py                       # Gradio 4-tab user interface
│   ├── config.py                    # Dataclass settings loaded from .env
│   ├── schemas.py                   # Frozen Pydantic data models
│   ├── service.py                   # QAService coordinator & routing logic
│   ├── ingestion/                   # Scanner, AST code parser, and splitters
│   ├── retrieval/                   # QdrantDenseStore, BM25, and HybridRetriever
│   ├── generation/                  # Generator, citations validator, and mock
│   └── web/                         # DuckDuckGo & Tavily search with domain allowlist
└── tests/                           # 106 unit & integration tests
```

---

## Documentation

- **[Environment Setup Guide](docs/ENV_SETUP_GUIDE.md):** Complete guide for setting up Gemini, Groq, Ollama, and Qdrant.
- **[Shared Architecture Contracts](docs/SHARED_CONTRACT.md):** Formal schemas and protocols connecting retrieval and generation.
- **[Evaluation Report](docs/EVALUATION.md):** Benchmark findings, token efficiency, and retrieval accuracy analysis.
- **[Integration Checklist](docs/INTEGRATION_CHECKLIST.md):** Verification status for all modules.

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
