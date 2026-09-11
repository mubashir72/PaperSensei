"""Session transitions shared by Streamlit and offline tests."""
from modules.adaptive_engine import new_performance, record_answer, decrease_difficulty
from modules.answer_evaluator import evaluate_answer
from modules.quiz_generator import validate_question


def new_session():
    return dict(source="", concepts=[], performance={}, question=None, feedback=None,
                history=[], followup=None, question_number=0)


def set_question(session, question):
    session["question"] = validate_question(question)
    session["feedback"] = None
    session["question_number"] += 1


def submit_answer(session, answer):
    if session["question"] is None:
        raise ValueError("Generate a question first.")
    if session["feedback"] is not None:
        raise ValueError("This answer has already been submitted.")
    question = session["question"]
    result = evaluate_answer(question, answer)
    topic = question["topic"]
    performance = session["performance"].get(topic, new_performance(topic))
    session["performance"][topic] = record_answer(performance, result["correct"])
    session["feedback"] = result
    session["history"].append({**question, **result})
    session["followup"] = None if result["correct"] else dict(
        topic=topic, difficulty=decrease_difficulty(question["difficulty"]))
    return result
