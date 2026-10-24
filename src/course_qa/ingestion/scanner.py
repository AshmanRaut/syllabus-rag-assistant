from pathlib import Path
from ..schemas import DiscoveredFile

EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff", ".c", ".h", ".txt", ".md"}

# Maps folder paths (relative to SOURCE_ROOT) → (subject, source_type, bucket).
# Both the actual lowercase_underscore layout (real notes/) and the
# title-case layout (used in tests and the original contract doc) are listed
# so the scanner works against real data AND the existing test fixtures.
FOLDER_MAP: dict[str, tuple[str, str, str]] = {
    # ── Actual on-disk layout (notes/ directory) ──────────────────────────
    "aoa_codes":              ("AOA",     "code",             "code"),
    "aoa_notes/Typed":        ("AOA",     "typed_pdf",        "typed"),
    "aoa_notes/Handwritten":  ("AOA",     "handwritten_pdf",  "handwritten"),
    "ds_codes":               ("DS",      "code",             "code"),
    "ds_notes/Handwritten":   ("DS",      "handwritten_pdf",  "handwritten"),
    "syllabus":               ("UNKNOWN", "syllabus",         "syllabus"),
    # ── Title-case layout kept for test fixtures ───────────────────────────
    "AOA codes":              ("AOA",     "code",             "code"),
    "AOA notes/Typed":        ("AOA",     "typed_pdf",        "typed"),
    "AOA notes/Handwritten":  ("AOA",     "handwritten_pdf",  "handwritten"),
    "DS codes":               ("DS",      "code",             "code"),
    "DS notes/Typed":         ("DS",      "typed_pdf",        "typed"),
    "DS notes/Handwritten":   ("DS",      "handwritten_pdf",  "handwritten"),
    "syllabi":                ("UNKNOWN", "syllabus",         "syllabus"),
}

# Root-level PDFs inside aoa_notes/ that are NOT in Typed/ or Handwritten/
# are exam/practice papers → treated as typed AOA PDFs.
_AOA_NOTES_ROOT_SUBJECTS = ("AOA", "typed_pdf", "typed")


class FolderScanner:
    def scan(self, root: Path) -> list[DiscoveredFile]:
        root = root.expanduser().resolve()
        found: list[DiscoveredFile] = []
        if not root.exists():
            return found

        seen_abs: set[str] = set()

        def _add(path: Path, subject: str, source_type: str, bucket: str) -> None:
            abs_str = str(path)
            if abs_str in seen_abs:
                return
            seen_abs.add(abs_str)
            actual_type = source_type
            suf = path.suffix.lower()
            if bucket in ("typed", "handwritten") and suf != ".pdf":
                actual_type = "image" if suf in {".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff"} else "text"
            if bucket == "code" and suf not in {".c", ".h"}:
                actual_type = "text"
            found.append(DiscoveredFile(
                absolute_path=abs_str,
                relative_path=path.relative_to(root).as_posix(),
                subject=subject,  # type: ignore[arg-type]
                source_type=actual_type,  # type: ignore[arg-type]
                bucket=bucket,  # type: ignore[arg-type]
            ))

        for rel_dir, (subject, source_type, bucket) in FOLDER_MAP.items():
            directory = root / rel_dir
            if not directory.exists():
                continue
            for path in sorted(directory.rglob("*")):
                if not path.is_file() or path.suffix.lower() not in EXTENSIONS:
                    continue
                _add(path, subject, source_type, bucket)

        # Exam / practice PDFs that sit directly in aoa_notes/ (not in a sub-folder).
        aoa_notes_dir = root / "aoa_notes"
        if aoa_notes_dir.exists():
            subject, source_type, bucket = _AOA_NOTES_ROOT_SUBJECTS
            for path in sorted(aoa_notes_dir.glob("*.pdf")):
                if path.is_file():
                    _add(path, subject, source_type, bucket)

        # Syllabus PDFs in a syllabus/ sub-folder (actual layout) OR at the root level.
        for path in sorted(root.glob("*Syllabus*.pdf")):
            if path.is_file():
                _add(path, "UNKNOWN", "syllabus", "syllabus")

        return found
