import re
from dataclasses import dataclass

SECTION = re.compile(
    r"(?im)^\s*((?:CHAPTER\s+[IVXLC]+\s*[-—:]?[^\n]*|(?:SECTION\s+)?\d+[A-Z]?(?:\.\d+)*\s*[.)-]?\s*(?:section|chapter)?\s*[^\n]{0,180}))\s*$"
)


@dataclass
class Chunk:
    text: str
    section: str
    page_number: int | None
    parent_id: str
    child_index: int


def split_sections(
    text: str,
    page_number: int | None = None,
    max_chars: int = 2200,
    overlap_chars: int = 200,
) -> list[Chunk]:
    if max_chars < 1 or overlap_chars < 0 or overlap_chars >= max_chars:
        raise ValueError("Require max_chars > overlap_chars >= 0")
    step = max_chars - overlap_chars
    matches = list(SECTION.finditer(text))
    if not matches:
        clean = text.strip()
        parts = [clean[i : i + max_chars] for i in range(0, len(clean), step)]
        return [
            Chunk(p, "UNKNOWN", page_number, "document", i)
            for i, p in enumerate(parts)
            if p
        ]
    chunks = []
    for idx, match in enumerate(matches):
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        body = text[match.start() : end].strip()
        parent = f"section-{idx + 1}"
        for child, start in enumerate(range(0, len(body), step)):
            chunks.append(
                Chunk(
                    body[start : start + max_chars],
                    match.group(1).strip(),
                    page_number,
                    parent,
                    child,
                )
            )
    return chunks
