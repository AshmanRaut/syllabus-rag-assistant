from course_qa.generation.citations import retain_only_cited_sources
from course_qa.schemas import CitationRecord

def test_invalid_citations_are_removed_and_only_valid_used_sources_returned():
    records = [CitationRecord(label="S1", source_kind="note", source_file="a.pdf", source_id="chunk1")]
    answer, used, warnings = retain_only_cited_sources("This is true [S1]. Unsupported [S99].", records)
    assert "[S1]" in answer
    assert "S99" not in answer
    assert len(used) == 1 and used[0].label == "S1"
    assert warnings

def test_no_citations_warns():
    answer, used, warnings = retain_only_cited_sources("Uncited claim.", [])
    assert not used
    assert any("no valid evidence" in w.lower() for w in warnings)
