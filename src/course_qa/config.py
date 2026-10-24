from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class Settings:
    source_root: Path = Path(os.getenv("SOURCE_ROOT", "./notes"))
    qdrant_url: str = os.getenv("QDRANT_URL", "http://localhost:6333").strip()
    qdrant_api_key: str | None = os.getenv("QDRANT_API_KEY") or None
    qdrant_collection: str = os.getenv("QDRANT_COLLECTION", "course_chunks")
    qdrant_local_path: Path = Path(os.getenv("QDRANT_LOCAL_PATH", "./.data/qdrant"))
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    dense_top_k: int = int(os.getenv("DENSE_TOP_K", "8"))
    bm25_top_k: int = int(os.getenv("BM25_TOP_K", "8"))
    hybrid_top_k: int = int(os.getenv("HYBRID_TOP_K", "5"))
    rrf_k: int = int(os.getenv("RRF_K", "60"))
    generator_provider: str = os.getenv("GENERATOR_PROVIDER", "openai_compatible")
    llm_base_url: str = os.getenv("LLM_BASE_URL", "")
    llm_api_key: str = os.getenv("LLM_API_KEY", "")
    llm_model: str = os.getenv("LLM_MODEL", "")
    llm_temperature: float = float(os.getenv("LLM_TEMPERATURE", "0.1"))
    web_search_mode: str = os.getenv("WEB_SEARCH_MODE", "auto")
    tavily_api_key: str = os.getenv("TAVILY_API_KEY", "")
    web_max_results: int = int(os.getenv("WEB_MAX_RESULTS", "5"))
    web_extract_full_text: bool = os.getenv("WEB_EXTRACT_FULL_TEXT", "false").lower() == "true"
    ocr_provider: str = os.getenv("OCR_PROVIDER", "disabled")
    ocr_max_pages: int = int(os.getenv("OCR_MAX_PAGES", "5"))  # 0 means unlimited
    ocr_cache_dir: Path = Path(os.getenv("OCR_CACHE_DIR", "./data/processed/ocr_cache"))
    page_image_dir: Path = Path(os.getenv("PAGE_IMAGE_DIR", "./data/page_images"))
    chunks_jsonl: Path = Path(os.getenv("CHUNKS_JSONL", "./data/processed/chunks.jsonl"))
    bm25_index_path: Path = Path(os.getenv("BM25_INDEX_PATH", "./data/index/bm25.json"))
    source_manifest: Path = Path(os.getenv("SOURCE_MANIFEST", "./data/processed/source_manifest.json"))

settings = Settings()
