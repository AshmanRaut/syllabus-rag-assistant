from __future__ import annotations
import hashlib
import json
from pathlib import Path
from importlib.metadata import PackageNotFoundError, version
from typing import Protocol

class OCRProvider(Protocol):
    provider_version: str
    def transcribe(self, image_path: Path) -> str: ...

class CachedOCR:
    """Cache one transcription per rendered-page hash + provider version; writes atomically."""
    def __init__(self, provider: OCRProvider, cache_dir: Path):
        self.provider = provider
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _key(self, image_path: Path) -> tuple[str, str]:
        digest = hashlib.sha256(image_path.read_bytes()).hexdigest()
        key = hashlib.sha256(f"{self.provider.provider_version}:{digest}".encode()).hexdigest()
        return digest, key

    def is_cached(self, image_path: Path) -> bool:
        _, key = self._key(image_path)
        record = self.cache_dir / f"{key}.json"
        if not record.exists(): return False
        try:
            payload = json.loads(record.read_text(encoding="utf-8"))
            return payload.get("key") == key and isinstance(payload.get("text"), str) and bool(payload.get("text", "").strip())
        except Exception:
            return False

    def transcribe(self, image_path: Path) -> str:
        digest, key = self._key(image_path)
        record = self.cache_dir / f"{key}.json"
        markdown_record = self.cache_dir / f"{key}.md"
        if record.exists():
            try: return str(json.loads(record.read_text(encoding="utf-8"))["text"])
            except Exception: record.unlink(missing_ok=True)
        text = self.provider.transcribe(image_path)
        # Do not cache empty failures: the next resumed run should retry the page.
        if not isinstance(text, str) or not text.strip():
            return ""
        temp = record.with_suffix(".tmp")
        temp.write_text(json.dumps({"key": key, "image_sha256": digest,
            "provider_version": self.provider.provider_version, "text": text}, ensure_ascii=False), encoding="utf-8")
        temp.replace(record)
        markdown_temp = markdown_record.with_suffix(".md.tmp")
        markdown_temp.write_text(text, encoding="utf-8")
        markdown_temp.replace(markdown_record)
        return text

class PaddleOCRVLProvider:
    """Optional PaddleOCR-VL adapter; import only when OCR is enabled.

    The current official Python integration uses `from paddleocr import PaddleOCRVL`,
    followed by `pipeline.predict(path)`. Validate installation and model downloads on
    representative pages before processing the full library.
    """
    def __init__(self, device: str = "cpu"):
        try:
            from paddleocr import PaddleOCRVL
        except ImportError as exc:
            raise RuntimeError("OCR_PROVIDER=paddleocr_vl but paddleocr is not installed. See requirements-ocr.txt and the official hardware guide.") from exc
        try: package_version = version("paddleocr")
        except PackageNotFoundError: package_version = "unknown"
        self.provider_version = f"paddleocr-vl:{package_version}:device={device}"
        self.pipeline = PaddleOCRVL(device=device)

    @staticmethod
    def _extract_markdown(res: object) -> str:
        markdown = getattr(res, "markdown", None)
        if isinstance(markdown, str): return markdown
        if isinstance(markdown, dict):
            if isinstance(markdown.get("text"), str): return markdown["text"]
            parts = markdown.get("markdown_texts", [])
            if isinstance(parts, list):
                texts = [str(p.get("text", "")) if isinstance(p, dict) else str(p) for p in parts]
                return "\n\n".join(t for t in texts if t.strip())
        return ""

    def transcribe(self, image_path: Path) -> str:
        output = self.pipeline.predict(str(image_path))
        results = list(output) if not isinstance(output, (list, tuple)) else output
        texts = [self._extract_markdown(res) for res in results]
        combined = "\n\n".join(t for t in texts if t.strip()).strip()
        if combined: return combined
        # Fallback to the model's public Markdown export if the result object shape changes.
        temp_dir = image_path.parent / ".ocr_export_tmp"
        temp_dir.mkdir(parents=True, exist_ok=True)
        for i, res in enumerate(results):
            try: res.save_to_markdown(save_path=str(temp_dir))
            except Exception: continue
        exports = sorted(temp_dir.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
        if exports:
            result = exports[0].read_text(encoding="utf-8", errors="replace").strip()
            for p in temp_dir.glob("*.md"): p.unlink(missing_ok=True)
            return result
        return ""
