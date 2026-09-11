"""Task 1 boundary for the teammate-owned PDF module. No extraction here."""
import importlib
from config import MAX_UPLOAD_BYTES, MAX_SOURCE_CHARS


def pdf_available():
    return importlib.util.find_spec("modules.pdf_processor") is not None


def read_uploaded_pdf(file):
    if not file.name.lower().endswith(".pdf"):
        raise ValueError("Choose a PDF file.")
    if file.size == 0:
        raise ValueError("This file is empty.")
    if file.size > MAX_UPLOAD_BYTES:
        raise ValueError("Each PDF must be 20 MB or smaller.")
    file.seek(0)
    header = file.read(5)
    file.seek(0)
    if header != b"%PDF-":
        raise ValueError("This file does not have a valid PDF header.")
    if not pdf_available():
        raise ValueError("PDF extraction is awaiting Task 2. Use pasted text in the meantime.")
    processor = importlib.import_module("modules.pdf_processor")
    try:
        result = processor.extract_pdf(file)
    except Exception as exc:
        raise ValueError("This PDF could not be read. Try another text-based PDF.") from exc
    if not isinstance(result, dict) or not isinstance(result.get("filename"), str):
        raise ValueError("PDF processor returned an invalid document.")
    if type(result.get("total_pages")) is not int or result["total_pages"] < 1:
        raise ValueError("PDF processor returned an invalid page count.")
    if not isinstance(result.get("pages"), list) or not isinstance(result.get("full_text"), str):
        raise ValueError("PDF processor must return pages and full_text.")
    seen = set()
    for page in result["pages"]:
        if (not isinstance(page, dict) or type(page.get("page_number")) is not int
                or not 1 <= page["page_number"] <= result["total_pages"]
                or page["page_number"] in seen or not isinstance(page.get("text"), str)):
            raise ValueError("PDF processor returned invalid page references.")
        seen.add(page["page_number"])
    if not result["full_text"].strip() or not any(p["text"].strip() for p in result["pages"]):
        raise ValueError("No readable text found. Scanned PDFs need OCR, planned for a future version.")
    return result


def document_source(document):
    text = "\n\n".join(f'[Page {p["page_number"]}]\n{p["text"]}' for p in document["pages"] if p["text"].strip())
    if len(text) > MAX_SOURCE_CHARS:
        raise ValueError(f"Select a smaller chapter or paper (at most {MAX_SOURCE_CHARS:,} characters). Large-document chunking belongs to Task 2.")
    return text
