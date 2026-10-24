from course_qa.config import settings
from course_qa.ingestion.scanner import FolderScanner

if __name__ == "__main__":
    files = FolderScanner().scan(settings.source_root)
    print(f"SOURCE_ROOT: {settings.source_root.resolve()}")
    print(f"Discovered: {len(files)} files")
    for f in files:
        print(f"{f.subject:7} {f.source_type:16} {f.relative_path}")
    if not files:
        print("No supported files found. Check SOURCE_ROOT and exact expected folder names in README.md.")
