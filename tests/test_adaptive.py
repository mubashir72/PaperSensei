import pytest
from modules.adaptive_engine import new_performance, record_answer
from modules.session_manager import new_session, set_question, submit_answer


def test_progression_and_bounds():
    p = new_performance("Energy")
    assert p["current_difficulty"] == "medium"
    p = record_answer(p, True)
    assert p["current_difficulty"] == "medium"
    p = record_answer(p, True)
    assert p["current_difficulty"] == "hard"
    for _ in range(4):
        p = record_answer(p, True)
    assert p["current_difficulty"] == "hard"
    for _ in range(6):
        p = record_answer(p, False)
    assert p["current_difficulty"] == "easy"
    assert p["correct_count"] == p["incorrect_count"] == 6


def test_mixed_results_break_streak():
    p = record_answer(new_performance("Energy"), True)
    p = record_answer(p, False)
    p = record_answer(p, True)
    assert p["current_difficulty"] == "medium"
    assert p["correct_streak"] == 1
    assert p["incorrect_streak"] == 0


def test_wrong_answer_followup_and_no_double_count(question):
    session = new_session()
    set_question(session, question)
    submit_answer(session, "B")
    assert session["followup"] == {"topic": "Photosynthesis", "difficulty": "easy"}
    assert session["performance"]["Photosynthesis"]["current_difficulty"] == "medium"
    with pytest.raises(ValueError, match="already"):
        submit_answer(session, "A")
    assert len(session["history"]) == 1
    set_question(session, {**question, "difficulty": "easy"})
    submit_answer(session, "A")
    assert session["followup"] is None


def test_topic_independence_and_reset(question):
    session = new_session()
    for _ in range(2):
        set_question(session, question)
        submit_answer(session, "A")
    set_question(session, {**question, "topic": "Respiration"})
    submit_answer(session, "B")
    assert session["performance"]["Photosynthesis"]["current_difficulty"] == "hard"
    assert session["performance"]["Respiration"]["current_difficulty"] == "medium"
    assert new_session()["history"] == []
    assert new_session()["performance"] == {}


def test_no_answer_does_not_change_state(question):
    session = new_session()
    set_question(session, question)
    with pytest.raises(ValueError):
        submit_answer(session, None)
    assert session["performance"] == {}
    assert session["feedback"] is None
