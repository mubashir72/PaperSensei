import pytest
from modules.groq_service import extract_concepts, generate_question, get_groq_client

def test_extract_concepts_success():
    sample_text = "Mitochondria generate most of the chemical energy needed to power biochemical reactions."
    concepts = extract_concepts(sample_text)
    assert isinstance(concepts, list)

def test_generate_question_schema():
    sample_text = "Photosynthesis requires sunlight to produce glucose."
    q = generate_question(sample_text, topic="Photosynthesis", difficulty="medium")
    assert "question" in q
    assert "options" in q
    assert "correct_answer" in q

def test_missing_api_key_failure(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    with pytest.raises(ValueError):
        get_groq_client()