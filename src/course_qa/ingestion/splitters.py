from __future__ import annotations
import hashlib
import re
import uuid
from typing import Iterable
from ..schemas import DiscoveredFile, SourceChunk

NAMESPACE = uuid.UUID("be98a96d-4e24-4e68-83ca-8a5a3b4afcd0")

def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()

def split_text(text: str, max_chars: int = 1100, overlap: int = 160) -> list[str]:
    """Paragraph-aware splitter with a simple character-window fallback."""
    text = re.sub(r"\r\n?", "\n", text).strip()
    if not text:
        return []
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if len(paragraph) > max_chars:
            if current:
                chunks.append(current); current = ""
            start = 0
            while start < len(paragraph):
                end = min(len(paragraph), start + max_chars)
                chunks.append(paragraph[start:end])
                if end == len(paragraph): break
                start = max(start + 1, end - overlap)
            continue
        candidate = f"{current}\n\n{paragraph}".strip()
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current: chunks.append(current)
            current = paragraph
    if current: chunks.append(current)
    return chunks

def chunks_for_text(text: str, file: DiscoveredFile, *, page_number: int | None = None,
                    function_name: str | None = None, title: str | None = None,
                    image_path: str | None = None, ocr_status: str = "not_needed") -> list[SourceChunk]:
    source_hash = sha256_text(file.relative_path)
    out = []
    for i, part in enumerate(split_text(text)):
        content_hash = sha256_text(part)
        stable = str(uuid.uuid5(NAMESPACE, f"{file.relative_path}|{page_number}|{function_name}|{i}|{content_hash}"))
        out.append(SourceChunk(
            chunk_id=stable, source_id=f"src_{source_hash[:16]}", subject=file.subject,
            source_type=file.source_type, source_file=file.relative_path,
            page_number=page_number, function_name=function_name, title=title or file.relative_path,
            text=part, image_path=image_path, content_hash=content_hash, source_hash=source_hash,
            chunk_index=i, ocr_status=ocr_status
        ))
    return out
