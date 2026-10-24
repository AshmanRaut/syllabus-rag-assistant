from __future__ import annotations
import re
from ..schemas import CitationRecord, RetrievedChunk, WebSource

LABEL_RE = re.compile(r"\[S(\d+)\]")

def build_labelled_evidence(notes: list[RetrievedChunk], web: list[WebSource]):
    records: list[CitationRecord] = []
    blocks: list[str] = []
    for hit in notes:
        chunk = hit.chunk
        label = f"S{len(records) + 1}"
        kind = "code" if chunk.source_type == "code" else ("syllabus" if chunk.source_type == "syllabus" else "note")
        records.append(CitationRecord(label=label, source_kind=kind, source_file=chunk.source_file,
            page_number=chunk.page_number, function_name=chunk.function_name, title=chunk.title,
            image_path=chunk.image_path, source_id=chunk.chunk_id))
        locator = f"{chunk.source_file}"
        if chunk.page_number is not None: locator += f", page {chunk.page_number}"
        if chunk.function_name: locator += f", function {chunk.function_name}"
        blocks.append(f"[{label}] TYPE={chunk.source_type}; SUBJECT={chunk.subject}; LOCATOR={locator}\n{chunk.text}")
    for source in web:
        label = f"S{len(records) + 1}"
        records.append(CitationRecord(label=label, source_kind="web", url=source.url,
            title=source.title, source_id=source.source_id))
        blocks.append(f"[{label}] TYPE=web; TITLE={source.title}; URL={source.url}; DOMAIN={source.domain}\n{source.text or source.snippet}")
    return "\n\n".join(blocks), records

def retain_only_cited_sources(answer: str, records: list[CitationRecord]) -> tuple[str, list[CitationRecord], list[str]]:
    by_label = {record.label: record for record in records}
    mentioned = LABEL_RE.findall(answer)
    invalid = sorted({f"S{x}" for x in mentioned if f"S{x}" not in by_label})
    if invalid:
        answer = LABEL_RE.sub(lambda m: m.group(0) if f"S{m.group(1)}" in by_label else "", answer)
    used_labels = list(dict.fromkeys(f"S{x}" for x in LABEL_RE.findall(answer) if f"S{x}" in by_label))
    used = [by_label[label] for label in used_labels]
    warnings = [f"Removed invalid citation label(s): {', '.join(invalid)}"] if invalid else []
    if not used:
        warnings.append("The generated answer cited no valid evidence; review grounding before relying on it.")
    return answer.strip(), used, warnings
