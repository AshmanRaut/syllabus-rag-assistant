"""course_qa.generation public API.

Exports the generator factory and both generator implementations so that
Contributor D can import directly from ``course_qa.generation``:

    from course_qa.generation import create_generator, MockGenerator
"""
from __future__ import annotations

from .generator import MockGenerator, OpenAICompatibleGenerator, create_generator
from .citations import build_labelled_evidence, retain_only_cited_sources

__all__ = [
    "create_generator",
    "MockGenerator",
    "OpenAICompatibleGenerator",
    "build_labelled_evidence",
    "retain_only_cited_sources",
]
