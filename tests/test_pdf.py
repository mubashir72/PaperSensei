"""Task 1 upload boundary tests, using a fake Task 2 extractor."""
import io
from types import SimpleNamespace
import pytest
from modules import document_gateway as gateway


class Upload(io.BytesIO):
    def __init__(self, content=b"%PDF-1.7 example", name="chapter.pdf", size=None):
        super().__init__(content)
        self.name = name
        self.size = len(content) if size is None else size


@pytest.mark.parametrize("upload,message", [
    (Upload(b""), "empty"), (Upload(b"invalid"), "header"),
    (Upload(name="chapter.txt"), "Choose a PDF"),
    (Upload(size=21 * 1024 * 1024), "20 MB")])
def test_bad_upload(upload, message):
    with pytest.raises(ValueError, match=message):
        gateway.read_uploaded_pdf(upload)


def test_pending_teammate_module(monkeypatch):
    monkeypatch.setattr(gateway, "pdf_available", lambda: False)
    with pytest.raises(ValueError, match="Task 2"):
        gateway.read_uploaded_pdf(Upload())


def install_fake(monkeypatch, document):
    monkeypatch.setattr(gateway, "pdf_available", lambda: True)
    monkeypatch.setattr(gateway.importlib, "import_module", lambda name: SimpleNamespace(extract_pdf=lambda f: document))


def test_valid_pdf_contract(monkeypatch):
    document = dict(filename="chapter.pdf", total_pages=2,
                    pages=[dict(page_number=2, text="Plants use sunlight.")], full_text="Plants use sunlight.")
    install_fake(monkeypatch, document)
    assert gateway.read_uploaded_pdf(Upload()) == document
    assert gateway.document_source(document) == "[Page 2]\nPlants use sunlight."


@pytest.mark.parametrize("document,message", [
    (dict(filename="scan.pdf", total_pages=1, pages=[dict(page_number=1, text="")], full_text=""), "OCR"),
    (dict(filename="bad.pdf", total_pages=1, pages=[dict(page_number=2, text="text")], full_text="text"), "references"),
    ({}, "invalid document")])
def test_bad_extractor_output(monkeypatch, document, message):
    install_fake(monkeypatch, document)
    with pytest.raises(ValueError, match=message):
        gateway.read_uploaded_pdf(Upload())


def test_large_extracted_text():
    with pytest.raises(ValueError, match="smaller"):
        gateway.document_source({"pages": [{"page_number": 1, "text": "a" * 24001}]})
