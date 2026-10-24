from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, Field, ConfigDict

Subject = Literal["DS", "AOA", "UNKNOWN"]
SourceType = Literal["typed_pdf", "handwritten_pdf", "image", "code", "syllabus", "web", "text"]

class SourceChunk(BaseModel):
    """Canonical indexed chunk shared by ingestion, retrieval, generation, and UI."""
    model_config = ConfigDict(extra="forbid")
    chunk_id: str
    source_id: str
    subject: Subject
    source_type: SourceType
    source_file: str  # path relative to SOURCE_ROOT, not an absolute user path
    page_number: int | None = None
    function_name: str | None = None
    module: str | None = None
    title: str | None = None
    text: str
    image_path: str | None = None  # relative under generated data/page_images or a stable asset path
    content_hash: str
    source_hash: str
    chunk_index: int = 0
    ocr_status: Literal["not_needed", "pending", "processed", "failed", "manual"] = "not_needed"
    extra_metadata: dict[str, Any] = Field(default_factory=dict)

class RetrievedChunk(BaseModel):
    chunk: SourceChunk
    score: float
    channel: Literal["dense", "bm25", "hybrid"]
    rank: int | None = None

class WebSource(BaseModel):
    source_id: str
    title: str
    url: str
    domain: str
    snippet: str
    retrieved_at: str
    text: str | None = None
    source_type: Literal["web"] = "web"

class CitationRecord(BaseModel):
    label: str  # e.g. S1; presentation uses [S1]
    source_kind: Literal["note", "code", "syllabus", "web"]
    source_file: str | None = None
    page_number: int | None = None
    function_name: str | None = None
    url: str | None = None
    title: str | None = None
    image_path: str | None = None
    source_id: str

class AnswerRequest(BaseModel):
    question: str
    subject: Subject | None = None
    use_web: bool = False
    answer_style: Literal["concise", "exam"] = "exam"

class AnswerResponse(BaseModel):
    answer: str
    citations: list[CitationRecord]
    notes_used: int
    web_used: int
    abstained: bool = False
    warnings: list[str] = Field(default_factory=list)

class DiscoveredFile(BaseModel):
    absolute_path: str
    relative_path: str
    subject: Subject
    source_type: SourceType
    bucket: Literal["typed", "handwritten", "code", "syllabus", "other"]

class IngestReport(BaseModel):
    discovered: int = 0          # files found by FolderScanner
    processed: int = 0           # files processed without an exception
    chunks_written: int = 0      # total valid chunks available in the resulting cache
    skipped_cached: int = 0      # page transcripts reused from OCR cache
    needs_ocr: int = 0           # manifest pages in pending/failed OCR state
    failed: int = 0              # files that raised an ingestion exception
    errors: list[str] = Field(default_factory=list)
