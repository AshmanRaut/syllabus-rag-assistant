from __future__ import annotations
from pathlib import Path
from hashlib import sha256
import shutil
from pypdf import PdfReader
from ..config import settings
from ..schemas import IngestReport, SourceChunk
from .scanner import FolderScanner
from .code_parser import parse_code_file
from .pdf_parser import parse_pdf
from .ocr import CachedOCR, PaddleOCRVLProvider
from .splitters import chunks_for_text

def create_ocr_provider():
    if settings.ocr_provider.lower() in {"paddleocr_vl", "paddleocr-vl", "paddleocr"}:
        return CachedOCR(PaddleOCRVLProvider(device="cpu"), settings.ocr_cache_dir)
    return None

def ingest_all(*, resume: bool = True, max_ocr_pages: int | None = None) -> tuple[list[SourceChunk], IngestReport]:
    scanner = FolderScanner()
    files = scanner.scan(settings.source_root)
    report = IngestReport(discovered=len(files))
    all_chunks: list[SourceChunk] = []
    settings.page_image_dir.mkdir(parents=True, exist_ok=True)
    ocr = create_ocr_provider()
    max_pages = settings.ocr_max_pages if max_ocr_pages is None else max_ocr_pages
    ocr_budget = [max_pages] if max_pages > 0 else None
    for file in files:
        try:
            path = Path(file.absolute_path)
            if path.suffix.lower() == ".pdf":
                # PdfReader import is used to inspect page count only when needed for diagnostics.
                chunks = parse_pdf(file, source_root=settings.source_root,
                    image_dir=settings.page_image_dir, ocr=ocr, manifest_path=settings.source_manifest,
                    ocr_budget=ocr_budget)
                all_chunks.extend(chunks)
            elif file.source_type == "code":
                all_chunks.extend(parse_code_file(file))
            elif path.suffix.lower() in {".txt", ".md"}:
                all_chunks.extend(chunks_for_text(path.read_text(encoding="utf-8", errors="replace"), file, title=path.name))
            elif path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff"}:
                if ocr is None:
                    report.needs_ocr += 1
                    report.errors.append(f"Pending OCR: {file.relative_path}")
                    continue
                cache_hit = ocr.is_cached(path)
                if ocr_budget is not None and ocr_budget[0] <= 0 and not cache_hit:
                    report.needs_ocr += 1
                    report.errors.append(f"OCR page limit reached: {file.relative_path}")
                    continue
                text = ocr.transcribe(path).strip()
                if ocr_budget is not None and not cache_hit: ocr_budget[0] -= 1
                image_key = sha256(file.relative_path.encode()).hexdigest()[:16]
                display_copy = settings.page_image_dir / f"source_{image_key}{path.suffix.lower()}"
                display_copy.parent.mkdir(parents=True, exist_ok=True)
                if not display_copy.exists(): shutil.copy2(path, display_copy)
                all_chunks.extend(chunks_for_text(text, file, image_path=display_copy.as_posix(), title=path.name, ocr_status="processed") if text else [])
            report.processed += 1
        except Exception as exc:
            report.failed += 1
            report.errors.append(f"{file.relative_path}: {type(exc).__name__}: {exc}")
    settings.chunks_jsonl.parent.mkdir(parents=True, exist_ok=True)
    existing: dict[str, SourceChunk] = {}
    if resume and settings.chunks_jsonl.exists():
        for line in settings.chunks_jsonl.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    c = SourceChunk.model_validate_json(line); existing[c.chunk_id] = c
                except Exception: pass
    existing.update({c.chunk_id: c for c in all_chunks})
    # Import from Module B's retrieval layer; fall back to an inline writer if unavailable.
    try:
        from ..retrieval.hybrid import save_chunks as _save_chunks
    except Exception:
        def _save_chunks(chunks: list, path: Path) -> None:  # type: ignore[misc]
            path.parent.mkdir(parents=True, exist_ok=True)
            temp = path.with_suffix(path.suffix + ".tmp")
            with temp.open("w", encoding="utf-8") as fh:
                for c in chunks:
                    fh.write(c.model_dump_json() + "\n")
            temp.replace(path)
    _save_chunks(list(existing.values()), settings.chunks_jsonl)
    report.chunks_written = len(existing)
    # Manifest is authoritative for page-level OCR statuses; these are page-level counts.
    if settings.source_manifest.exists():
        try:
            import json
            manifest = json.loads(settings.source_manifest.read_text(encoding="utf-8"))
            report.needs_ocr = sum(1 for item in manifest.values() if item.get("ocr_status") in {"pending", "failed"})
            report.skipped_cached = sum(1 for item in manifest.values() if item.get("cache_hit_this_run") is True)
        except Exception: pass
    return list(existing.values()), report
