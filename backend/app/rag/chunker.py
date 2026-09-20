import re
from dataclasses import dataclass

from app.utils.text import clean_text, normalize_whitespace


@dataclass
class DocumentChunk:
    text: str
    section: str
    page: int


@dataclass
class ParsedGuideline:
    title: str
    organization: str
    version: str
    status: str
    condition: str
    chunks: list[DocumentChunk]


HEADER_PATTERN = re.compile(r"^([A-Z][A-Z _/]+):\s*(.*)$")
SECTION_SPLIT_PATTERN = re.compile(r"^SECTION:\s*(.+)$", re.MULTILINE)


def parse_guideline_document(raw_text: str, condition: str) -> ParsedGuideline:
    text = clean_text(raw_text)
    lines = text.split("\n")

    metadata: dict[str, str] = {}
    body_start = 0
    for idx, line in enumerate(lines):
        match = HEADER_PATTERN.match(line.strip())
        if match and match.group(1) in {"GUIDELINE", "VERSION", "ORGANIZATION", "STATUS"}:
            metadata[match.group(1)] = match.group(2).strip()
            body_start = idx + 1
        elif line.strip() == "" and body_start > 0:
            continue
        elif body_start > 0:
            break

    body = "\n".join(lines[body_start:]).strip()

    sections: list[DocumentChunk] = []
    matches = list(SECTION_SPLIT_PATTERN.finditer(body))
    if not matches:
        sections.append(DocumentChunk(text=normalize_whitespace(body), section="General", page=1))
    else:
        for page, match in enumerate(matches, start=1):
            section_name = match.group(1).strip()
            start = match.end()
            end = matches[page].start() if page < len(matches) else len(body)
            section_text = normalize_whitespace(body[start:end])
            if section_text:
                sections.append(DocumentChunk(text=section_text, section=section_name, page=page))

    return ParsedGuideline(
        title=metadata.get("GUIDELINE", "Untitled Synthetic Guideline"),
        organization=metadata.get("ORGANIZATION", "Synthetic Clinical Guideline Consortium"),
        version=metadata.get("VERSION", "1.0"),
        status=metadata.get("STATUS", "DEMONSTRATION DATA"),
        condition=condition,
        chunks=sections,
    )


def chunk_section_text(text: str, max_chars: int = 600) -> list[str]:
    if len(text) <= max_chars:
        return [text]

    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        if current and len(current) + len(sentence) + 1 > max_chars:
            chunks.append(current.strip())
            current = sentence
        else:
            current = f"{current} {sentence}".strip()
    if current:
        chunks.append(current.strip())
    return chunks
