from collections import defaultdict
from modules.groq_service import _call_groq
from utils.json_parser import clean_and_parse_json
from prompts.analysis_prompts import QUESTION_SEGMENTATION_PROMPT, TOPIC_CLASSIFICATION_PROMPT

DISCLAIMER = "These topics appeared most frequently in the uploaded papers. This analysis does not guarantee future exam questions."

def segment_questions(raw_text: str) -> list:
    prompt = QUESTION_SEGMENTATION_PROMPT.format(raw_text=raw_text)
    raw = _call_groq(prompt, expect_json=False)
    data = clean_and_parse_json(raw)
    if isinstance(data, list):
        return [str(q) for q in data]
    return data.get("questions", []) if isinstance(data, dict) else []

def analyze_past_papers(papers_text_list: list) -> dict:
    all_questions = []
    for paper in papers_text_list:
        all_questions.extend(segment_questions(paper))

    if not all_questions:
        return {"topics": [], "disclaimer": DISCLAIMER}

    # Only process first 5 questions per test run to stay strictly within token limits
    prompt = TOPIC_CLASSIFICATION_PROMPT.format(questions=all_questions[:5])
    raw = _call_groq(prompt, expect_json=False)
    classified = clean_and_parse_json(raw)
    if isinstance(classified, dict):
        classified = classified.get("questions", [])

    total_questions = len(classified) if isinstance(classified, list) else 0
    topic_map = defaultdict(lambda: {"frequency": 0, "types": set(), "years": set()})

    if isinstance(classified, list):
        for item in classified:
            if not isinstance(item, dict):
                continue
            top = item.get("topic", "General").title()
            topic_map[top]["frequency"] += 1
            if item.get("question_type"):
                topic_map[top]["types"].add(item["question_type"])
            if item.get("year"):
                try:
                    topic_map[top]["years"].add(int(item["year"]))
                except (ValueError, TypeError):
                    pass

    topics_summary = []
    for topic, stats in topic_map.items():
        percentage = round((stats["frequency"] / total_questions) * 100) if total_questions else 0
        topics_summary.append({
            "topic": topic,
            "frequency": stats["frequency"],
            "percentage": percentage,
            "question_types": list(stats["types"]),
            "years_found": sorted(list(stats["years"]))
        })

    topics_summary.sort(key=lambda x: x["frequency"], reverse=True)

    return {
        "topics": topics_summary,
        "disclaimer": DISCLAIMER
    }