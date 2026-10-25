from __future__ import annotations

import re
from ..schemas import CitationRecord, RetrievedChunk, WebSource

LABEL_RE = re.compile(r"\[S(\d+)\]")

# Chunks with these OCR statuses contain no useful text; skip them when building
# the evidence context so the LLM does not see "[pending OCR]" as evidence.
_SKIP_OCR_STATUSES = {"pending", "failed"}


def _chunk_has_usable_text(chunk_text: str, ocr_status: str) -> bool:
    """Return True when a chunk has text worth including as LLM evidence."""
    if ocr_status in _SKIP_OCR_STATUSES:
        return False
    stripped = chunk_text.strip()
    return bool(stripped) and stripped != "[pending OCR]"


def build_labelled_evidence(
    notes: list[RetrievedChunk],
    web: list[WebSource],
) -> tuple[str, list[CitationRecord]]:
    """Assign sequential [S1], [S2], … labels to usable evidence sources.

    Chunks whose text is empty or whose OCR status is pending/failed are
    silently skipped; they carry no grounding value and confuse the model.
    Web sources with no snippet or text are also skipped.

    Returns:
        context: A single multi-block string to embed in the LLM prompt.
        records: The matching CitationRecord list, in label order.
    """
    records: list[CitationRecord] = []
    blocks: list[str] = []

    for hit in notes:
        chunk = hit.chunk
        if not _chunk_has_usable_text(chunk.text, chunk.ocr_status):
            continue
        label = f"S{len(records) + 1}"
        kind: str
        if chunk.source_type == "code":
            kind = "code"
        elif chunk.source_type == "syllabus":
            kind = "syllabus"
        else:
            kind = "note"
        records.append(
            CitationRecord(
                label=label,
                source_kind=kind,  # type: ignore[arg-type]
                source_file=chunk.source_file,
                page_number=chunk.page_number,
                function_name=chunk.function_name,
                title=chunk.title,
                image_path=chunk.image_path,
                source_id=chunk.chunk_id,
            )
        )
        locator = chunk.source_file
        if chunk.page_number is not None:
            locator += f", page {chunk.page_number}"
        if chunk.function_name:
            locator += f", function {chunk.function_name}"
        blocks.append(
            f"[{label}] TYPE={chunk.source_type}; SUBJECT={chunk.subject}; LOCATOR={locator}\n{chunk.text}"
        )

    for source in web:
        body = (source.text or source.snippet or "").strip()
        if not body:
            continue
        label = f"S{len(records) + 1}"
        records.append(
            CitationRecord(
                label=label,
                source_kind="web",
                url=source.url,
                title=source.title,
                source_id=source.source_id,
            )
        )
        blocks.append(
            f"[{label}] TYPE=web; TITLE={source.title}; URL={source.url}; DOMAIN={source.domain}\n{body}"
        )

    return "\n\n".join(blocks), records


def retain_only_cited_sources(
    answer: str,
    records: list[CitationRecord],
) -> tuple[str, list[CitationRecord], list[str]]:
    """Strip invalid citation labels from *answer* and return only used records.

    Algorithm:
    1. Find every [Sn] in the answer.
    2. Classify each as valid (has a matching record) or invalid.
    3. Remove invalid labels from the answer text.
    4. Collect used records in mention order (preserving document order ties).
    5. Emit warnings for removed labels and for uncited answers.

    Returns:
        (cleaned_answer, used_records, warnings)
    """
    by_label = {record.label: record for record in records}
    mentioned = LABEL_RE.findall(answer)

    invalid_labels = sorted({f"S{x}" for x in mentioned if f"S{x}" not in by_label})

    if invalid_labels:
        answer = LABEL_RE.sub(
            lambda m: m.group(0) if f"S{m.group(1)}" in by_label else "",
            answer,
        )

    # Re-scan after removal so duplicate labels don't produce duplicate records.
    used_labels = list(
        dict.fromkeys(f"S{x}" for x in LABEL_RE.findall(answer) if f"S{x}" in by_label)
    )
    used = [by_label[label] for label in used_labels]

    warnings: list[str] = []
    if invalid_labels:
        warnings.append(f"Removed invalid citation label(s): {', '.join(invalid_labels)}")
    if not used:
        warnings.append(
            "The generated answer cited no valid evidence; "
            "review grounding before relying on it."
        )
    return answer.strip(), used, warnings
