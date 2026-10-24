from course_qa.schemas import SourceChunk, RetrievedChunk, CitationRecord
from course_qa.ingestion.splitters import split_text, chunks_for_text
from course_qa.ingestion.code_parser import extract_c_functions
from course_qa.schemas import DiscoveredFile

def test_chunk_schema_rejects_missing_required_source_metadata():
    chunk = SourceChunk(chunk_id="00000000-0000-0000-0000-000000000001", source_id="src_a",
        subject="DS", source_type="code", source_file="DS codes/a.c", text="void f() {}",
        content_hash="h", source_hash="s", function_name="f")
    assert chunk.function_name == "f"
    assert SourceChunk.model_validate_json(chunk.model_dump_json()).chunk_id == chunk.chunk_id

def test_splitter_overlap_and_content():
    parts = split_text("a" * 1400, max_chars=600, overlap=100)
    assert len(parts) >= 3
    assert all(parts)
    assert "a" * 100 in parts[0] + parts[1]

def test_code_function_extraction():
    source = "int add(int a, int b) { return a+b; }\nvoid reverse(void) { int x = 1; }"
    funcs = extract_c_functions(source)
    assert [name for name, _ in funcs] == ["add", "reverse"]

def test_scanner_respects_requested_folder_layout(tmp_path):
    from course_qa.ingestion.scanner import FolderScanner
    (tmp_path / "AOA codes").mkdir()
    (tmp_path / "DS notes" / "Handwritten").mkdir(parents=True)
    (tmp_path / "AOA codes" / "Dijkstra.c").write_text("int f(void) { return 1; }")
    (tmp_path / "DS notes" / "Handwritten" / "linked.pdf").write_bytes(b"fake")
    found = FolderScanner().scan(tmp_path)
    lookup = {f.relative_path: f for f in found}
    assert lookup["AOA codes/Dijkstra.c"].subject == "AOA"
    assert lookup["AOA codes/Dijkstra.c"].source_type == "code"
    assert lookup["DS notes/Handwritten/linked.pdf"].subject == "DS"
    assert lookup["DS notes/Handwritten/linked.pdf"].bucket == "handwritten"
