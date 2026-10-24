import argparse
from course_qa.ingestion.runner import ingest_all

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--resume", action="store_true", help="Merge prior chunks by stable chunk ID")
    parser.add_argument("--max-ocr-pages", type=int, default=None,
        help="Maximum uncached OCR pages this run; 0 means unlimited. Existing cache hits do not consume budget.")
    args = parser.parse_args()
    chunks, report = ingest_all(resume=args.resume, max_ocr_pages=args.max_ocr_pages)
    print(report.model_dump_json(indent=2))
    print(f"Total cached chunks: {len(chunks)}")
