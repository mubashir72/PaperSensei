"""Shared validation for ordinary and remedial MCQs."""
import re
from config import DIFFICULTIES


def validate_question(data, topic=None, difficulty=None):
    if not isinstance(data, dict):
        raise ValueError("Expected a question object.")
    if data.get("insufficient_source"):
        raise ValueError("The source does not contain enough information for this question.")
    for field in ("question", "explanation", "topic"):
        if not isinstance(data.get(field), str) or not data[field].strip() or data[field] == "N/A":
            raise ValueError(f"Question is missing a valid {field}.")
    options = data.get("options")
    if not isinstance(options, list) or len(options) != 4:
        raise ValueError("An MCQ must have four options.")
    cleaned = []
    for option in options:
        if not isinstance(option, str) or not option.strip():
            raise ValueError("Each option must contain text.")
        cleaned.append(re.sub(r"^[A-Da-d][.)]\s*", "", option.strip()).strip())
    if any(not option for option in cleaned) or len(set(s.casefold() for s in cleaned)) != 4:
        raise ValueError("Options must be nonempty and distinct.")
    answer = data.get("correct_answer")
    if not isinstance(answer, str) or answer.strip().upper() not in ("A", "B", "C", "D"):
        raise ValueError("Correct answer must be A, B, C, or D.")
    if data.get("difficulty") not in DIFFICULTIES:
        raise ValueError("Invalid question difficulty.")
    if topic and data["topic"].strip().casefold() != topic.strip().casefold():
        raise ValueError("Question topic differs from the requested concept.")
    if difficulty and data["difficulty"] != difficulty:
        raise ValueError("Question difficulty differs from the requested level.")
    page = data.get("source_page")
    if page is not None and (type(page) is not int or page < 1):
        raise ValueError("Source page must be a positive integer or null.")
    return {**data, "topic": topic or data["topic"].strip(),
            "options": [f"{letter}. {option}" for letter, option in zip("ABCD", cleaned)],
            "correct_answer": answer.strip().upper(), "source_page": page}
