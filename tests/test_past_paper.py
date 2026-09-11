import pytest
from modules.past_paper_analyzer import analyze_past_papers, DISCLAIMER

def test_analyze_past_papers_success():
    sample_papers = [
        "Annual Exam 2024: Q1. Define Photosynthesis. Q2. What is Respiration?",
        "Annual Exam 2022: Q1. Explain the mechanism of Photosynthesis in detail."
    ]
    result = analyze_past_papers(sample_papers)
    assert "topics" in result
    assert result["disclaimer"] == DISCLAIMER
    if result["topics"]:
        top = result["topics"][0]
        assert "topic" in top
        assert "frequency" in top
        assert "percentage" in top
        assert "question_types" in top
        assert "years_found" in top

def test_empty_paper_handling():
    result = analyze_past_papers([])
    assert result == {"topics": [], "disclaimer": DISCLAIMER}