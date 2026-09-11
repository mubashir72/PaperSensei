import pytest


@pytest.fixture
def question():
    return dict(question="What powers photosynthesis?",
                options=["A. Sunlight", "B. Sound", "C. Wind", "D. Gravity"],
                correct_answer="A", explanation="Plants use sunlight to produce glucose.",
                topic="Photosynthesis", difficulty="medium", source_page=None)


@pytest.fixture(autouse=True)
def no_live_ai(monkeypatch):
    from modules import groq_service
    def blocked(*args, **kwargs):
        raise AssertionError("Tests must not call the live Groq API.")
    monkeypatch.setattr(groq_service, "get_groq_client", blocked)
