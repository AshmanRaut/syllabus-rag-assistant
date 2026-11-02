# Environment Configuration Guide (`.env`)

This guide provides a comprehensive, field-by-field walkthrough for configuring the **Syllabus-Aware Course QA Assistant** via your local [`.env`](file:///Users/ashmanraut/Ashman/Fr.%20CRCE/NLP/syllabus-rag-assistant/.env) file.

---

## Table of Contents
1. [Quick Start (30 Seconds)](#quick-start-30-seconds)
2. [Configuration Reference](#configuration-reference)
   - [1. Course Materials & Ingestion](#1-course-materials--ingestion)
   - [2. Vector Database (Qdrant)](#2-vector-database-qdrant)
   - [3. Embedding & Hybrid Search Retrieval](#3-embedding--hybrid-search-retrieval)
   - [4. LLM Generation (The Core Engine)](#4-llm-generation-the-core-engine)
   - [5. Web Search Augmentation](#5-web-search-augmentation)
   - [6. OCR (Optical Character Recognition)](#6-ocr-optical-character-recognition)
   - [7. Processed Data & Cache Paths](#7-processed-data--cache-paths)
3. [LLM Provider Recipes](#llm-provider-recipes)
   - [Recipe A: Google Gemini (Recommended)](#recipe-a-google-gemini-free--recommended)
   - [Recipe B: Groq Cloud](#recipe-b-groq-cloud)
   - [Recipe C: Local Ollama (100% Offline & Free)](#recipe-c-local-ollama-100-offline--free)
   - [Recipe D: Official OpenAI](#recipe-d-official-openai)
   - [Recipe E: OpenRouter](#recipe-e-openrouter)
   - [Recipe F: Offline Deterministic Mock (Zero Keys Needed)](#recipe-f-offline-deterministic-mock-zero-keys-needed)
4. [Troubleshooting & Common Pitfalls](#troubleshooting--common-pitfalls)

---

## Quick Start (30 Seconds)

1. **Copy the example configuration:**
   ```bash
   cp .env.example .env
   ```
2. **Open `.env` in your editor and choose an LLM provider:**
   - For Google Gemini (free API key from [Google AI Studio](https://aistudio.google.com/app/apikey)):
     ```env
     LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
     LLM_API_KEY=AIzaSy...your_gemini_api_key_here...
     LLM_MODEL=gemini-3.5-flash
     LLM_MAX_TOKENS=8192
     ```
   - Or run completely offline with **zero keys** (leave `LLM_MODEL=` empty).
3. **Launch the application:**
   ```bash
   python run.py
   ```

> [!CAUTION]
> **Never commit your `.env` file to version control.** It contains secret API keys. The repository's [`.gitignore`](file:///Users/ashmanraut/Ashman/Fr.%20CRCE/NLP/syllabus-rag-assistant/.gitignore) is pre-configured to ignore `.env`.

---

## Configuration Reference

### 1. Course Materials & Ingestion

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `SOURCE_ROOT` | `./notes` | Root folder containing your course materials. Subdirectories include syllabus PDFs, lecture slide PDFs, and `.c` source code files for DS and AOA. |

---

### 2. Vector Database (Qdrant)

The system supports both embedded local mode (zero installation) and client-server Docker mode.

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `QDRANT_URL` | *(empty)* | If using remote or Dockerized Qdrant, set to `http://localhost:6333`. **Leave blank** to use embedded local SQLite/file mode. |
| `QDRANT_COLLECTION` | `course_chunks` | Name of the collection where vector embeddings are indexed. |
| `QDRANT_LOCAL_PATH` | `./.data/qdrant` | Disk path where the embedded Qdrant SQLite database and payload store are saved. |
| `QDRANT_API_KEY` | *(empty)* | Optional API key if using a managed Qdrant Cloud cluster. |

Option A — Docker (recommended)

Pull and start Qdrant
docker run -d \
  --name qdrant \
  -p 6333:6333 \
  -v $(pwd)/.data/qdrant:/qdrant/storage \
  qdrant/qdrant

Verify it's running
curl http://localhost:6333/healthz
should return: {"title":"qdrant - vector search engine", ...}

Option B — Docker Compose (already in the repo)

docker compose up -d qdrant

.env setting — no change needed:
env
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION=course_chunks

> [!IMPORTANT]
> **Qdrant Local File Lock:** When running in embedded mode (`QDRANT_LOCAL_PATH`), the local database is locked by the active Python process. If you want to rebuild the index (`python scripts/index.py --rebuild`), stop `python run.py` first with `Ctrl+C`.

---

### 3. Embedding & Hybrid Search Retrieval

Retrieval combines dense semantic search (Qdrant) and lexical keyword search (BM25) fused via Reciprocal Rank Fusion (RRF).

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | HuggingFace embedding model (384 dimensions). Runs locally on CPU/Apple Silicon MPS with zero API costs. |
| `DENSE_TOP_K` | `12` | Candidate retrieval depth from the Qdrant semantic vector index. |
| `BM25_TOP_K` | `12` | Candidate retrieval depth from the lexical BM25 index. |
| `HYBRID_TOP_K` | `10` | Final number of fused candidates passed to the LLM generator as evidence. |
| `RRF_K` | `60` | Reciprocal Rank Fusion smoothing constant ($1 / (k + \text{rank})$). Standard value is `60`. |

---

### 4. LLM Generation (The Core Engine)

The generator uses an OpenAI-compatible interface, enabling plug-and-play support for Gemini, Groq, OpenAI, Ollama, and OpenRouter.

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `LLM_BASE_URL` | *(empty)* | Base endpoint URL of the OpenAI-compatible provider. |
| `LLM_API_KEY` | *(empty)* | Secret authentication key for the provider. |
| `LLM_MODEL` | *(empty)* | Model identifier. **If left empty**, the assistant automatically falls back to `MockGenerator` (offline mode). |
| `LLM_TEMPERATURE` | `0.1` | Sampling temperature. Low values (`0.0` - `0.2`) enforce factual, strict grounding and avoid hallucinations. |
| `LLM_MAX_TOKENS` | `8192` | Maximum output token budget. Controls full C code generation and complete 6-section exam answers. |

---

### 5. Web Search Augmentation

Augments course notes when the user enables web search in the UI and queries outside the syllabus.

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `WEB_SEARCH_MODE` | `auto` | Search backend: `auto`, `tavily`, `ddgs`, or `off`. `auto` prefers Tavily if `TAVILY_API_KEY` is set, else falls back to DuckDuckGo. |
| `TAVILY_API_KEY` | *(empty)* | Optional API key for [Tavily Search](https://tavily.com/). Leave empty to use DuckDuckGo keyless search. |
| `WEB_MAX_RESULTS` | `5` | Maximum number of external web snippets retrieved per query. |
| `WEB_EXTRACT_FULL_TEXT` | `false` | When `true`, scrapes the full page body instead of just the search result snippet. |

---

### 6. OCR (Optical Character Recognition)

Extracts text from handwritten notes and diagram-heavy slide scans.

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `OCR_PROVIDER` | `disabled` | Set to `disabled` for pre-processed notes or `paddleocr_vl` for local visual language OCR. |
| `OCR_MAX_PAGES` | `5` | Maximum uncached pages to process per ingestion run (`0` = unlimited). |
| `OCR_CACHE_DIR` | `./data/processed/ocr_cache` | Path where extracted OCR text is cached per page hash. |

Right now 281 handwritten pages are marked pending. Skip OCR for the MVP demo; add it later.
Skip OCR (current default — fine for demo)
Typed PDFs and C code already produce 575 indexed chunks without OCR.

Enable PaddleOCR-VL (when you're ready):

WARNING: large install (~3GB), requires Python 3.10-3.12
python3.12 -m venv .venv-ocr
.venv-ocr/bin/pip install -e ".[ocr]"

Test on 5 pages:
OCR_PROVIDER=paddleocr_vl OCR_MAX_PAGES=5 \
  .venv-ocr/bin/python scripts/ingest.py --resume

env
OCR_PROVIDER=paddleocr_vl
OCR_MAX_PAGES=5

---

### 7. Processed Data & Cache Paths

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `PAGE_IMAGE_DIR` | `./data/page_images` | Folder where 150 DPI PDF slide scans are rendered for inline citations. |
| `CHUNKS_JSONL` | `./data/processed/chunks.jsonl` | Canonical JSONL file holding all parsed course notes and code chunks. |
| `BM25_INDEX_PATH` | `./data/index/bm25.json` | Serialized BM25 vocabulary and document frequency index. |
| `SOURCE_MANIFEST` | `./data/processed/source_manifest.json` | Ingestion tracking manifest mapping source files and checksums. |

---

## LLM Provider Recipes

### Recipe A: Google Gemini (Free & Recommended)
Google AI Studio offers a free tier with **1,000,000 Tokens Per Minute (TPM)** and up to **65,536 output tokens**, making it ideal for full C code files and extensive exam answers.

1. Get a free API key at **[Google AI Studio](https://aistudio.google.com/app/apikey)**.
2. Put this in your `.env`:
   ```env
   LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
   LLM_API_KEY=AIzaSy...your_gemini_key...
   LLM_MODEL=gemini-3.5-flash
   LLM_TEMPERATURE=0.1
   LLM_MAX_TOKENS=8192
   ```

> [!NOTE]
> The assistant automatically configures `reasoning_effort="low"` for Gemini models so that internal reasoning tokens do not consume your visible token budget.

---

### Recipe B: Groq Cloud
Groq provides ultra-fast inference on LPUs.

1. Get an API key from **[Groq Console](https://console.groq.com/keys)**.
2. Put this in your `.env`:
   ```env
   LLM_BASE_URL=https://api.groq.com/openai/v1
   LLM_API_KEY=gsk_...your_groq_key...
   LLM_MODEL=qwen/qwen3.8-27b
   LLM_TEMPERATURE=0.1
   LLM_MAX_TOKENS=900
   ```

> [!WARNING]
> **Groq Free Tier OTPM Limitation:** Groq's free tier enforces a strict limit of **1,000 Output Tokens Per Minute (OTPM)** on `qwen/qwen3.8-27b`. Setting `LLM_MAX_TOKENS` above 950 will cause a `429 RateLimitError`. For long code generation, use Gemini or local Ollama instead.

---

### Recipe C: Local Ollama (100% Offline & Free)
Run open-weights models locally on your Mac with zero internet required, zero rate limits, and full privacy.

1. Download and install [Ollama](https://ollama.com/).
2. Pull a model in your terminal:
   ```bash
   ollama run llama3.2
   # Or for dedicated coding:
   ollama run qwen2.5-coder:7b
   ```
3. Put this in your `.env`:
   ```env
   LLM_BASE_URL=http://localhost:11434/v1
   LLM_API_KEY=ollama
   LLM_MODEL=llama3.2
   LLM_TEMPERATURE=0.1
   LLM_MAX_TOKENS=4096
   ```

---

### Recipe D: Official OpenAI
1. Get an API key from **[OpenAI Platform](https://platform.openai.com/api-keys)**.
2. Put this in your `.env`:
   ```env
   LLM_BASE_URL=https://api.openai.com/v1
   LLM_API_KEY=sk-proj-...your_openai_key...
   LLM_MODEL=gpt-4o-mini
   LLM_TEMPERATURE=0.1
   LLM_MAX_TOKENS=4096
   ```

---

### Recipe E: OpenRouter
Access dozens of free and paid models through a single gateway.

1. Sign up at **[OpenRouter](https://openrouter.ai/)**.
2. Put this in your `.env`:
   ```env
   LLM_BASE_URL=https://openrouter.ai/api/v1
   LLM_API_KEY=sk-or-v1-...your_openrouter_key...
   LLM_MODEL=meta-llama/llama-3.3-70b-instruct:free
   LLM_TEMPERATURE=0.1
   LLM_MAX_TOKENS=4096
   ```

---

### Recipe F: Offline Deterministic Mock (Zero Keys Needed)
If you want to evaluate retrieval accuracy, test the UI, run automated grading, or work with zero internet:

```env
LLM_BASE_URL=
LLM_API_KEY=
LLM_MODEL=
```

Leaving `LLM_MODEL` blank instructs the assistant to use [`MockGenerator`](file:///Users/ashmanraut/Ashman/Fr.%20CRCE/NLP/syllabus-rag-assistant/src/course_qa/generation/generator.py#L50-L94). It performs real dense + sparse retrieval, retrieves actual slide scans, and grounds citations deterministically without external LLM dependencies.

---

## Troubleshooting & Common Pitfalls

### 1. `RateLimitError: 429 - Request too large on output tokens per minute (OTPM)`
- **Cause:** Using Groq free tier with `LLM_MAX_TOKENS` set higher than 950.
- **Solution:** Reduce `LLM_MAX_TOKENS=900` in `.env`, or switch to Gemini (`gemini-3.5-flash`), which allows 1,000,000 TPM.

### 2. `RuntimeError: Storage folder .data/qdrant is already accessed by another instance`
- **Cause:** You ran `python scripts/index.py --rebuild` while `python run.py` was actively running in another terminal window.
- **Solution:** Press `Ctrl+C` to stop `run.py`, perform the re-indexing, and then start `run.py` again.

### 3. Code output or answers cut off mid-sentence
- **Cause:** Token budget exhausted.
- **Solution:**
  1. Set `LLM_MAX_TOKENS=8192` in `.env`.
  2. In the UI, ensure **Answer Style** is set to `exam` if you need full multi-section explanations and code.

### 4. "Status: Abstained" on topics that exist in your notes
- **Cause:** Subject Filter mismatch.
- **Explanation:** In this syllabus, **Data Structures (DS)** and **Analysis of Algorithms (AOA)** are separate modules. For instance, Dynamic Programming, Greedy Knapsack, and Graph algorithms are in **AOA**. If the UI dropdown is set to **`DS`**, all AOA files are excluded from retrieval.
- **Solution:** Set the **Subject Filter** dropdown to **`Any`** or **`AOA`**.

### 5. `NotFoundError: 404 - The model does not exist or you do not have access to it`
- **Cause:** The provider deprecated or renamed the model ID, or your API key lacks permissions for that model.
- **Solution:**
  - On Gemini: Use `gemini-3.5-flash`.
  - On Groq: Use `qwen/qwen3.8-27b`.
  - On OpenAI: Use `gpt-4o-mini`.

---

## Provider Comparison Summary

| Provider | Cost | Rate Limit (TPM) | Max Output Tokens | Offline? | Best Used For |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Google Gemini Flash** | Free | 1,000,000 | 65,536 | No | **Default recommendation**: long code & exams |
| **Local Ollama** | Free | Unlimited | Hardware-dependent | **Yes** | 100% offline privacy & no internet |
| **Groq Cloud** | Free | 1,000 (OTPM) | ~900 | No | Fast, short queries |
| **OpenAI `gpt-4o-mini`** | Paid (low) | Tier-based | 16,384 | No | High-accuracy commercial baseline |
| **MockGenerator** | Free | Unlimited | N/A | **Yes** | Unit tests, benchmarking, offline CI |
