import json
from types import SimpleNamespace
import pytest
from modules import groq_service as ai
from modules.quiz_generator import validate_question
from modules.answer_evaluator import evaluate_answer
from utils.json_parser import clean_and_parse_json


def test_extract_concepts_success(monkeypatch):
    monkeypatch.setattr(ai, "_call_groq", lambda *a, **k: '{"concepts":["Energy","Energy"]}')
    assert ai.extract_concepts("Mitochondria supply energy.") == ["Energy"]
    assert ai.extract_concepts("") == []


@pytest.mark.parametrize("difficulty", ["easy", "medium", "hard"])
@pytest.mark.parametrize("answer,correct", [("A", True), ("B", False)])
def test_generate_and_grade(monkeypatch, question, difficulty, answer, correct):
    question["difficulty"] = difficulty
    monkeypatch.setattr(ai, "_call_groq", lambda *a, **k: json.dumps(question))
    result = ai.generate_question("Plants use sunlight.", "Photosynthesis", difficulty)
    assert evaluate_answer(result, answer)["correct"] is correct


@pytest.mark.parametrize("change", [
    {"options": ["one"]}, {"options": ["A. x", "B. x", "C. y", "D. z"]},
    {"correct_answer": "E"}, {"source_page": True}, {"difficulty": "expert"},
    {"question": ""}, {"explanation": "N/A"}, {"insufficient_source": True}])
def test_invalid_question(question, change):
    with pytest.raises(ValueError):
        validate_question({**question, **change})


@pytest.mark.parametrize("raw", ['{"question":"unfinished"', '["half",', "", "null", "123"])
def test_invalid_json_is_rejected(raw):
    with pytest.raises(ValueError):
        clean_and_parse_json(raw)


def test_fenced_json():
    assert clean_and_parse_json('```json\n{"concepts": []}\n```') == {"concepts": []}


def test_invalid_response_retries_once(monkeypatch, question):
    replies = iter(["not JSON", json.dumps(question)])
    monkeypatch.setattr(ai, "_call_groq", lambda *a, **k: next(replies))
    assert ai.generate_question("Plants use sunlight.", "Photosynthesis") == question


def test_repeated_bad_schema_fails(monkeypatch):
    calls = []
    def reply(*a, **k):
        calls.append(1)
        return '{"question":"Incomplete"}'
    monkeypatch.setattr(ai, "_call_groq", reply)
    with pytest.raises(ValueError):
        ai.generate_question("Plants use sunlight.", "Photosynthesis")
    assert len(calls) == 2


def test_missing_api_key_failure(monkeypatch):
    import config
    import streamlit as st
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setattr(st, "secrets", {})
    with pytest.raises(ValueError, match="GROQ_API_KEY"):
        config.get_api_key()


def test_streamlit_secret(monkeypatch):
    import config
    import streamlit as st
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setattr(st, "secrets", {"GROQ_API_KEY": "test-secret"})
    assert config.get_api_key() == "test-secret"


def test_truncated_completion(monkeypatch):
    completion = SimpleNamespace(choices=[SimpleNamespace(finish_reason="length")])
    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **k: completion)))
    monkeypatch.setattr(ai, "get_groq_client", lambda: client)
    with pytest.raises(ValueError, match="incomplete"):
        ai._call_groq("prompt")


def test_source_limit(monkeypatch):
    with pytest.raises(ValueError, match="24,000"):
        ai.extract_concepts("a" * 24001)


def test_followup_validated(monkeypatch, question):
    question["difficulty"] = "easy"
    monkeypatch.setattr(ai, "_call_groq", lambda *a, **k: json.dumps(question))
    assert ai.generate_followup_question("Photosynthesis", "Plants use sunlight.")["difficulty"] == "easy"


def test_invalid_concepts_fail(monkeypatch):
    monkeypatch.setattr(ai, "_call_groq", lambda *a, **k: '{"concepts":[1]}')
    with pytest.raises(ValueError):
        ai.extract_concepts("source")
