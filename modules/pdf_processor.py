"""Extract readable PDFs with page references; OCR is deliberately unsupported."""
import io
from pathlib import Path
import pdfplumber
from config import MAX_UPLOAD_BYTES
from utils.text_utils import clean_pages, source_sections

MAX_PAGES = 500
MAX_EXTRACTED_CHARS = 2_000_000


def extract_pdf(file):
    filename = Path(str(getattr(file, "name", "document.pdf"))).name
    if not filename.lower().endswith(".pdf"):
        raise ValueError("Choose a PDF file.")
    position = file.tell()
    try:
        file.seek(0)
        raw = file.read(MAX_UPLOAD_BYTES + 1)
    finally:
        file.seek(position)
    if not raw:
        raise ValueError("This PDF is empty.")
    if len(raw) > MAX_UPLOAD_BYTES:
        raise ValueError("Each PDF must be 20 MB or smaller.")
    if not raw.startswith(b"%PDF-"):
        raise ValueError("This file does not have a valid PDF header.")
    pages, scanned, total_chars = [], [], 0
    try:
        with pdfplumber.open(io.BytesIO(raw)) as pdf:
            if not pdf.pages:
                raise ValueError("This PDF has no pages.")
            if len(pdf.pages) > MAX_PAGES:
                raise ValueError(f"Use a PDF with at most {MAX_PAGES} pages. Split this file into chapters.")
            for number, page in enumerate(pdf.pages, 1):
                text = page.extract_text() or ""
                total_chars += len(text)
                if total_chars > MAX_EXTRACTED_CHARS:
                    raise ValueError("This PDF contains too much text. Split it into smaller chapters.")
                if not text.strip() and page.images:
                    scanned.append(number)
                pages.append({"page_number": number, "text": text})
                page.close()
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError("This PDF could not be read. It may be damaged or password-protected; upload an unlocked copy.") from exc
    pages = clean_pages(pages)
    full_text = "\n\n".join(p["text"] for p in pages if p["text"])
    if not full_text.strip():
        if scanned:
            raise ValueError("This PDF appears to contain scanned images only. OCR support is planned for a future version.")
        raise ValueError("No readable text found in this PDF. It may be blank or require OCR, planned for a future version.")
    empty = [p["page_number"] for p in pages if not p["text"]]
    warnings = []
    if empty:
        warnings.append("Pages without readable text: " + ", ".join(map(str, empty)) + ". They were not included in the study text.")
    if scanned:
        warnings.append("Some pages appear scanned. OCR is not supported, so their image content was not extracted.")
    return {"filename": filename, "total_pages": len(pages), "pages": pages,
            "full_text": full_text, "sections": source_sections(pages), "warnings": warnings}
