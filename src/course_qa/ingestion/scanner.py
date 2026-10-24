from pathlib import Path
from ..schemas import DiscoveredFile

EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff", ".c", ".h", ".txt", ".md"}

# Exact folder contract requested by the team. Category is inferred from directory names.
FOLDER_MAP = {
    "AOA codes": ("AOA", "code", "code"),
    "AOA notes/Typed": ("AOA", "typed_pdf", "typed"),
    "AOA notes/Handwritten": ("AOA", "handwritten_pdf", "handwritten"),
    "DS codes": ("DS", "code", "code"),
    "DS notes/Typed": ("DS", "typed_pdf", "typed"),
    "DS notes/Handwritten": ("DS", "handwritten_pdf", "handwritten"),
    "syllabi": ("UNKNOWN", "syllabus", "syllabus"),
}

class FolderScanner:
    def scan(self, root: Path) -> list[DiscoveredFile]:
        root = root.expanduser().resolve()
        found: list[DiscoveredFile] = []
        if not root.exists():
            return found
        for rel_dir, (subject, source_type, bucket) in FOLDER_MAP.items():
            directory = root / rel_dir
            if not directory.exists():
                continue
            for path in sorted(directory.rglob("*")):
                if not path.is_file() or path.suffix.lower() not in EXTENSIONS:
                    continue
                actual_type = source_type
                if bucket == "typed" and path.suffix.lower() != ".pdf":
                    actual_type = "image" if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff"} else "text"
                if bucket == "handwritten" and path.suffix.lower() != ".pdf":
                    actual_type = "image" if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff"} else "text"
                if bucket == "code" and path.suffix.lower() not in {".c", ".h"}:
                    actual_type = "text"
                found.append(DiscoveredFile(
                    absolute_path=str(path), relative_path=path.relative_to(root).as_posix(),
                    subject=subject, source_type=actual_type, bucket=bucket
                ))
        # A direct root-level syllabus PDF is accepted as a convenience too.
        for path in sorted(root.glob("*Syllabus*.pdf")):
            found.append(DiscoveredFile(absolute_path=str(path), relative_path=path.name,
                subject="UNKNOWN", source_type="syllabus", bucket="syllabus"))
        return found
