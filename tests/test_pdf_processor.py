import pytest
from modules.pdf_processor import extract_pdf
from modules.document_gateway import read_uploaded_pdf
from utils.text_utils import source_sections, clean_pages
from tests.pdf_fixtures import upload, pdf_bytes


def test_real_pdf_extraction_and_position():
    file = upload(["Photosynthesis uses sunlight.", "Respiration releases energy."])
    file.seek(7)
    document = extract_pdf(file)
    assert file.tell() == 7
    assert document["total_pages"] == 2
    assert document["pages"][1] == {"page_number": 2, "text": "Respiration releases energy."}
    assert "[Page 2]" in document["sections"][0]["text"]


def test_repeated_margins_removed_from_real_pdf():
    doc = extract_pdf(upload([f"Biology Notes\nConcept {i} uses energy.\nSome additional content.\nPage {i}" for i in range(1, 4)]))
    assert "Biology Notes" not in doc["full_text"]
    assert "Page 1" not in doc["full_text"]
    assert "Concept 1" in doc["full_text"]


def test_blank_pdf():
    with pytest.raises(ValueError, match="No readable text"):
        extract_pdf(upload([""]))


def test_scanned_pdf():
    with pytest.raises(ValueError, match="scanned"):
        extract_pdf(upload([""], image_only=True))


def test_mixed_blank_page_preserved():
    doc = read_uploaded_pdf(upload(["Plants use sunlight.", ""]))
    assert doc["pages"][1]["text"] == ""
    assert doc["warnings"]
    assert doc["total_pages"] == 2


def test_corrupt_pdf():
    file = upload(["text"])
    file.truncate(12)
    with pytest.raises(ValueError, match="damaged|read"):
        extract_pdf(file)


def test_no_pages():
    import io
    file = io.BytesIO(pdf_bytes([]))
    file.name = "empty.pdf"
    with pytest.raises(ValueError, match="no pages"):
        extract_pdf(file)


def test_large_real_pdf_sections_preserve_text():
    line = "Plants use sunlight and water to make glucose."
    doc = extract_pdf(upload(["\n".join([line] * 35)] * 20))
    assert len(doc["sections"]) > 1
    assert all(len(section["text"]) <= 24000 for section in doc["sections"])
    assert sum(section["text"].count("glucose.") for section in doc["sections"]) == doc["full_text"].count("glucose.")


def test_single_large_page_chunks_and_references():
    sections = source_sections([{"page_number": 9, "text": "abc " * 20000}])
    assert len(sections) > 1
    assert all(s["page_numbers"] == [9] and s["text"].startswith("[Page 9]") for s in sections)
    assert sum(s["text"].count("abc") for s in sections) == 20000


def test_page_limit(monkeypatch):
    import modules.pdf_processor as processor
    monkeypatch.setattr(processor, "MAX_PAGES", 1)
    with pytest.raises(ValueError, match="at most"):
        extract_pdf(upload(["one", "two"]))
