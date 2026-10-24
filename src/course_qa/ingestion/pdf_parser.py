from __future__ import annotations
import hashlib
import json
from pathlib import Path
from typing import Protocol
import fitz
from pypdf import PdfReader
from ..schemas import DiscoveredFile, SourceChunk
from .splitters import chunks_for_text

class OCRProvider(Protocol):
    def transcribe(self, image_path: Path) -> str: ...

class OCRUnavailable(RuntimeError): pass

class DisabledOCR:
    def transcribe(self, image_path: Path) -> str:
        raise OCRUnavailable("OCR is disabled. Page image retained and page recorded as pending OCR.")

def page_image_path(source_root: Path, relative_path: str, page: int, image_dir: Path) -> Path:
    rel_hash = hashlib.sha256(relative_path.encode()).hexdigest()[:12]
    target_dir = image_dir / rel_hash
    target_dir.mkdir(parents=True, exist_ok=True)
    return target_dir / f"page_{page:04d}.png"

def _save_manifest(manifest_path: Path | None, record: dict) -> None:
    if manifest_path is None: return
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    existing = {}
    if manifest_path.exists():
        try: existing = json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception: existing = {}
    key = f"{record['source_file']}#page={record['page_number']}"
    existing[key] = record
    temp = manifest_path.with_suffix(manifest_path.suffix + ".tmp")
    temp.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(manifest_path)

def parse_pdf(file: DiscoveredFile, *, source_root: Path, image_dir: Path,
              ocr: OCRProvider | None = None, min_text_chars: int = 35,
              manifest_path: Path | None = None, ocr_budget: list[int] | None = None) -> list[SourceChunk]:
    """Page-wise extraction with durable image/transcript status manifest.

    `ocr_budget=None` means unlimited. `ocr_budget=[N]` is a shared mutable budget across all
    files. CachedOCR pages do not consume the budget, so a resumed run can advance to new pages.
    """
    pdf_path = Path(file.absolute_path)
    reader = PdfReader(str(pdf_path))
    visual_doc = fitz.open(pdf_path)
    output: list[SourceChunk] = []
    for index, page in enumerate(reader.pages):
        page_number = index + 1
        text = (page.extract_text() or "").strip()
        visual = visual_doc[index]
        img_path = page_image_path(source_root, file.relative_path, page_number, image_dir)
        if not img_path.exists():
            pix = visual.get_pixmap(matrix=fitz.Matrix(1.6, 1.6), alpha=False)
            pix.save(img_path)
        image_hash = hashlib.sha256(img_path.read_bytes()).hexdigest()
        status = "not_needed"
        error = None
        cache_hit = False
        if len(text) >= min_text_chars and file.bucket != "handwritten":
            output.extend(chunks_for_text(text, file, page_number=page_number,
                image_path=img_path.as_posix(), title=f"{pdf_path.name} · page {page_number}"))
        else:
            cache_hit = bool(ocr is not None and hasattr(ocr, "is_cached") and ocr.is_cached(img_path))
            budget_exhausted = ocr_budget is not None and ocr_budget[0] <= 0 and not cache_hit
            if ocr is None:
                status, error = "pending", "OCR_PROVIDER disabled"
            elif budget_exhausted:
                status, error = "pending", "OCR page limit reached; rerun with a larger --max-ocr-pages value"
            else:
                try:
                    text = ocr.transcribe(img_path).strip()
                    status = "processed" if text else "failed"
                    if not text: error = "OCR provider returned empty text"
                    if ocr_budget is not None and not cache_hit: ocr_budget[0] -= 1
                except Exception as exc:
                    status, error = "failed", f"{type(exc).__name__}: {exc}"
            if text and status == "processed":
                output.extend(chunks_for_text(text, file, page_number=page_number,
                    image_path=img_path.as_posix(), title=f"{pdf_path.name} · page {page_number}", ocr_status="processed"))
        _save_manifest(manifest_path, {
            "source_file": file.relative_path, "subject": file.subject, "source_type": file.source_type,
            "page_number": page_number, "page_image": img_path.as_posix(), "image_sha256": image_hash,
            "ocr_status": status, "error": error, "text_chars": len(text),
            "transcript_cached": bool(ocr is not None and hasattr(ocr, "is_cached") and ocr.is_cached(img_path)),
            "cache_hit_this_run": bool(cache_hit),
        })
    visual_doc.close()
    return output
