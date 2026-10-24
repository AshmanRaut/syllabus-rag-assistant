from pathlib import Path
from course_qa.ingestion.ocr import CachedOCR

class FakeOCR:
    provider_version = "fake-1"
    def __init__(self): self.calls = 0
    def transcribe(self, image_path: Path) -> str:
        self.calls += 1
        return f"transcribed {image_path.name}"

def test_cached_ocr_does_not_repeat_provider_call(tmp_path):
    image = tmp_path / "page.png"
    image.write_bytes(b"fake image bytes")
    provider = FakeOCR()
    cached = CachedOCR(provider, tmp_path / "cache")
    assert cached.transcribe(image) == "transcribed page.png"
    assert (tmp_path / "cache").glob("*.md")
    assert cached.is_cached(image)
    assert cached.transcribe(image) == "transcribed page.png"
    assert provider.calls == 1

def test_empty_ocr_result_is_not_marked_as_cached(tmp_path):
    class EmptyOCR(FakeOCR):
        def transcribe(self, image_path: Path) -> str:
            self.calls += 1
            return ""
    image = tmp_path / "blank.png"
    image.write_bytes(b"fake blank bytes")
    provider = EmptyOCR()
    cached = CachedOCR(provider, tmp_path / "cache")
    assert cached.transcribe(image) == ""
    assert not cached.is_cached(image)
    assert cached.transcribe(image) == ""
    assert provider.calls == 2
