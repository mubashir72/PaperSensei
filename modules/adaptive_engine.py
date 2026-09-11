"""Pure topic-specific adaptive learning rules."""
from config import DIFFICULTIES


def increase_difficulty(level):
    return DIFFICULTIES[min(DIFFICULTIES.index(level) + 1, 2)]


def decrease_difficulty(level):
    return DIFFICULTIES[max(DIFFICULTIES.index(level) - 1, 0)]


def new_performance(topic):
    return dict(topic=topic, correct_count=0, incorrect_count=0,
                correct_streak=0, incorrect_streak=0, current_difficulty="medium")


def record_answer(performance, correct):
    if type(correct) is not bool:
        raise ValueError("Answer result must be a boolean.")
    result = dict(performance)
    own, other = ("correct", "incorrect") if correct else ("incorrect", "correct")
    result[f"{own}_count"] += 1
    result[f"{own}_streak"] += 1
    result[f"{other}_streak"] = 0
    if result[f"{own}_streak"] >= 2:
        change = increase_difficulty if correct else decrease_difficulty
        result["current_difficulty"] = change(result["current_difficulty"])
        result[f"{own}_streak"] = 0
    return result
