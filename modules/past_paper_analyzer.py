"""Task 4 analysis. Classify every question in bounded batches."""
import re
from collections import defaultdict
from modules.groq_service import _request_json, _source
from prompts.analysis_prompts import QUESTION_SEGMENTATION_PROMPT, TOPIC_CLASSIFICATION_PROMPT

DISCLAIMER = "These topics appeared most frequently in the uploaded papers. This analysis does not guarantee future exam questions."


def segment_questions(raw_text: str) -> list:
    if not raw_text.strip():
        return []
    def validate(data):
        questions = data.get("questions") if isinstance(data, dict) else data
        if not isinstance(questions, list) or any(not isinstance(q, str) or not q.strip() for q in questions):
            raise ValueError("Invalid segmented questions.")
        return [q.strip() for q in questions]
    return _request_json(QUESTION_SEGMENTATION_PROMPT.format(raw_text=_source(raw_text)), validate)


def analyze_past_papers(papers_text_list: list) -> dict:
    stats = defaultdict(lambda: {"frequency": 0, "types": set(), "years": set()})
    total = 0
    for paper in papers_text_list:
        questions = segment_questions(paper)
        # Only attribute a paper year if its header contains a single unambiguous year.
        header = re.split(r"\b(?:Q(?:uestion)?\s*\d+|1[.)])", paper, maxsplit=1, flags=re.I)[0][:300]
        years = set(re.findall(r"\b(?:19|20)\d{2}\b", header))
        year = int(next(iter(years))) if len(years) == 1 else None
        for start in range(0, len(questions), 5):
            batch = questions[start:start + 5]
            def validate(data):
                items = data.get("questions") if isinstance(data, dict) else data
                if not isinstance(items, list) or len(items) != len(batch):
                    raise ValueError("Classification must include every question in the batch.")
                for item in items:
                    if not isinstance(item, dict) or any(not isinstance(item.get(k), str) or not item[k].strip() for k in ("topic", "question_type")):
                        raise ValueError("Invalid topic classification.")
                    if item["question_type"] not in ("MCQ", "Short question", "Long question", "Numerical problem"):
                        raise ValueError("Invalid question format.")
                return items
            classified = _request_json(TOPIC_CLASSIFICATION_PROMPT.format(questions=batch), validate)
            for item in classified:
                topic = " ".join(item["topic"].split()).casefold()
                stats[topic]["frequency"] += 1
                stats[topic]["types"].add(item["question_type"])
                if year:
                    stats[topic]["years"].add(year)
                total += 1
    topics = [dict(topic=topic.title(), frequency=s["frequency"],
                   percentage=round(s["frequency"] / total * 100, 2),
                   question_types=sorted(s["types"]), years_found=sorted(s["years"]))
              for topic, s in stats.items()]
    topics.sort(key=lambda t: (-t["frequency"], t["topic"]))
    return {"topics": topics, "disclaimer": DISCLAIMER}
