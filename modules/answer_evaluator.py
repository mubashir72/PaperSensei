"""Deterministic MCQ grading."""
from modules.quiz_generator import validate_question


def evaluate_answer(question, student_answer):
    question = validate_question(question)
    if not isinstance(student_answer, str) or student_answer.strip().upper() not in ("A", "B", "C", "D"):
        raise ValueError("Select one answer before submitting.")
    answer = student_answer.strip().upper()
    return dict(correct=answer == question["correct_answer"], student_answer=answer,
                correct_answer=question["correct_answer"], explanation=question["explanation"])
