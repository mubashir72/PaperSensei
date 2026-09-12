"""Conservative text cleanup and page-preserving source sections."""
import re
import unicodedata
from collections import Counter
from config import MAX_SOURCE_CHARS


def clean_text(text):
    text = unicodedata.normalize("NFKC", text).replace("\x00", "")
    lines = [re.sub(r"[^\S\n]+", " ", line).strip() for line in text.splitlines()]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def clean_pages(pages):
    cleaned = [{**p, "text": clean_text(p["text"])} for p in pages]
    # Only remove repeated outer lines on 3+ pages, never repeated body text.
    for edge in (0, -1):
        candidates = []
        for page in cleaned:
            lines = page["text"].splitlines()
            candidates.append(lines[edge] if len(lines) >= 3 else "")
        counts = Counter(line for line in candidates if line and len(line) <= 100)
        repeated = {line for line, count in counts.items() if count >= max(3, len(pages) * .6)}
        for page, candidate in zip(cleaned, candidates):
            if candidate in repeated or re.fullmatch(r"(?:Page\s+)?\d+\s*(?:of\s+\d+)?", candidate, re.I):
                lines = page["text"].splitlines()
                del lines[edge]
                page["text"] = "\n".join(lines).strip()
    return cleaned


def source_sections(pages, limit=MAX_SOURCE_CHARS):
    """Return all text in bounded sections, repeating page markers after splits."""
    if limit < 64:
        raise ValueError("Source section limit must be at least 64 characters.")
    sections, current, numbers = [], "", []
    for page in pages:
        remaining = page["text"].strip()
        marker = f'[Page {page["page_number"]}]\n'
        while remaining:
            prefix = ("\n\n" if current else "") + marker
            room = limit - len(current) - len(prefix)
            if room < 32:
                sections.append({"text": current, "page_numbers": numbers})
                current, numbers = "", []
                continue
            cut = min(len(remaining), room)
            if cut < len(remaining):
                boundary = remaining.rfind("\n", 0, cut + 1)
                if boundary < cut // 2:
                    boundary = remaining.rfind(" ", 0, cut + 1)
                if boundary > 0:
                    cut = boundary
            current += prefix + remaining[:cut]
            if page["page_number"] not in numbers:
                numbers.append(page["page_number"])
            remaining = remaining[cut:].lstrip()
            if remaining:
                sections.append({"text": current, "page_numbers": numbers})
                current, numbers = "", []
    if current:
        sections.append({"text": current, "page_numbers": numbers})
    return sections
