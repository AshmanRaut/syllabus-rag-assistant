from __future__ import annotations
import re
from pathlib import Path
from ..schemas import DiscoveredFile, SourceChunk
from .splitters import chunks_for_text

# Lightweight parser for clean educational C files. Tree-sitter can replace this behind the same interface.
FUNCTION_START = re.compile(r"(?m)^\s*(?:[\w\*]+\s+)+(?P<name>[A-Za-z_]\w*)\s*\([^;{}]*\)\s*\{")

def extract_c_functions(source: str) -> list[tuple[str, str]]:
    result: list[tuple[str, str]] = []
    for match in FUNCTION_START.finditer(source):
        start = match.start()
        open_brace = source.find("{", match.start(), match.end())
        depth, i = 0, open_brace
        in_string = None; escaped = False; line_comment = False; block_comment = False
        while i < len(source):
            ch = source[i]; nxt = source[i + 1] if i + 1 < len(source) else ""
            if line_comment:
                if ch == "\n": line_comment = False
            elif block_comment:
                if ch == "*" and nxt == "/": block_comment = False; i += 1
            elif in_string:
                if escaped: escaped = False
                elif ch == "\\": escaped = True
                elif ch == in_string: in_string = None
            elif ch in ('"', "'"):
                in_string = ch
            elif ch == "/" and nxt == "/": line_comment = True; i += 1
            elif ch == "/" and nxt == "*": block_comment = True; i += 1
            elif ch == "{": depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    result.append((match.group("name"), source[start:i + 1]))
                    break
            i += 1
    # Deduplicate if declaration-shaped lines confused the small scanner.
    seen = set(); unique = []
    for name, body in result:
        key = (name, body)
        if key not in seen: unique.append((name, body)); seen.add(key)
    return unique

def parse_code_file(file: DiscoveredFile) -> list[SourceChunk]:
    path = Path(file.absolute_path)
    text = path.read_text(encoding="utf-8", errors="replace")
    functions = extract_c_functions(text)
    chunks: list[SourceChunk] = []
    if not functions:
        return chunks_for_text(text, file, title=path.name)
    for name, body in functions:
        chunks.extend(chunks_for_text(body, file, function_name=name, title=f"{path.name}::{name}"))
    return chunks
