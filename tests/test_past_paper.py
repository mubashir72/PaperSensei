import json
import pytest
from modules import groq_service as ai
from modules import past_paper_analyzer as analyzer


def test_all_questions_multiple_papers(monkeypatch):
    replies = iter([
        json.dumps({"questions": [f"Question {i}" for i in range(7)]}),
        json.dumps({"questions": [{"topic": "Photosynthesis", "question_type": "Short question"}] * 5}),
        json.dumps({"questions": [{"topic": " photosynthesis ", "question_type": "MCQ"}] * 2}),
        json.dumps({"questions": ["Respiration?"]}),
        json.dumps({"questions": [{"topic": "Respiration", "question_type": "Long question", "year": 1999}]})
    ])
    monkeypatch.setattr(ai, "_call_groq", lambda *a, **k: next(replies))
    result = analyzer.analyze_past_papers(["Annual Exam 2024: Q1. Define.", "Annual Exam 2022: Q1. Explain."])
    assert result["disclaimer"] == analyzer.DISCLAIMER
    assert result["topics"][0] == dict(topic="Photosynthesis", frequency=7, percentage=87.5,
                                     question_types=["MCQ", "Short question"], years_found=[2024])
    assert result["topics"][1]["years_found"] == [2022]


def test_single_paper_unknown_year(monkeypatch):
    replies = iter(['{"questions":["Define energy."]}',
                    '{"questions":[{"topic":"Energy","question_type":"Short question","year":2024}]}'])
    monkeypatch.setattr(ai, "_call_groq", lambda *a, **k: next(replies))
    result = analyzer.analyze_past_papers(["Q1. Define energy."])
    assert result["topics"][0]["percentage"] == 100
    assert result["topics"][0]["years_found"] == []


def test_empty_paper_handling():
    assert analyzer.analyze_past_papers([]) == {"topics": [], "disclaimer": analyzer.DISCLAIMER}
    assert analyzer.analyze_past_papers([" "])["topics"] == []


def test_incomplete_classification_rejected(monkeypatch):
    monkeypatch.setattr(analyzer, "segment_questions", lambda text: ["q1", "q2"])
    monkeypatch.setattr(ai, "_call_groq", lambda *a, **k: '{"questions":[{"topic":"Energy","question_type":"MCQ"}]}')
    with pytest.raises(ValueError, match="every question"):
        analyzer.analyze_past_papers(["paper"])
