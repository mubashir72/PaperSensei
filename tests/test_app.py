from streamlit.testing.v1 import AppTest
from modules import groq_service as ai


def click(app, label):
    next(b for b in app.button if b.label == label).click()
    return app.run()


def navigate(app, screen):
    next(r for r in app.radio if r.label == "Navigate").set_value(screen)
    return app.run()


def test_app_complete_quiz_and_reset(monkeypatch, question):
    monkeypatch.setattr(ai, "extract_concepts", lambda text: ["Photosynthesis"])
    monkeypatch.setattr(ai, "generate_question", lambda *args: dict(question))
    monkeypatch.setattr(ai, "generate_explanation", lambda *args: "Sunlight provides energy.")
    monkeypatch.setattr(ai, "generate_followup_question", lambda *args: {**question, "difficulty": "easy"})
    app = AppTest.from_file("app.py", default_timeout=10).run()
    assert not app.exception
    navigate(app, "Documents")
    app.text_area[0].set_value("Plants use sunlight to produce glucose.")
    click(app, "Extract concepts")
    navigate(app, "Quiz")
    click(app, "Generate next question")
    next(r for r in app.radio if r.label == "Choose an answer").set_value("B")
    click(app, "Submit answer")
    assert app.session_state["study"]["performance"]["Photosynthesis"]["incorrect_count"] == 1
    assert app.warning
    click(app, "Try easier follow-up")
    assert app.session_state["study"]["question"]["difficulty"] == "easy"
    next(r for r in app.radio if r.label == "Choose an answer").set_value("A")
    click(app, "Submit answer")
    navigate(app, "Session summary")
    assert app.metric[0].value == "2"
    click(app, "Reset session")
    assert app.session_state["study"]["history"] == []
    assert not app.exception


def test_error_keeps_source_and_progress(monkeypatch):
    app = AppTest.from_file("app.py", default_timeout=10).run()
    navigate(app, "Documents")
    def fail(text):
        raise ValueError("GROQ_API_KEY is missing.")
    monkeypatch.setattr(ai, "extract_concepts", fail)
    app.text_area[0].set_value("Source")
    click(app, "Extract concepts")
    assert "GROQ_API_KEY" in app.error[0].value
    assert app.session_state["study"]["source"] == ""
    assert not app.exception


def test_past_paper_ui(monkeypatch):
    import modules.past_paper_analyzer as analyzer
    monkeypatch.setattr(analyzer, "analyze_past_papers", lambda papers: {
        "topics": [dict(topic="Energy", frequency=2, percentage=100,
                        question_types=["MCQ"], years_found=[2024])],
        "disclaimer": analyzer.DISCLAIMER})
    app = AppTest.from_file("app.py", default_timeout=10).run()
    navigate(app, "Documents")
    next(r for r in app.radio if r.label == "Document type").set_value("Past paper").run()
    app.text_area[0].set_value("Annual Exam 2024: Q1. Define energy.")
    click(app, "Add past paper")
    navigate(app, "Past paper insights")
    click(app, "Analyze papers")
    assert len(app.dataframe) == 1
    assert not app.exception

