import os
from groq import Groq
from dotenv import load_dotenv
from utils.json_parser import clean_and_parse_json
from prompts.concept_prompts import CONCEPT_EXTRACTION_PROMPT
from prompts.quiz_prompts import QUIZ_GENERATION_PROMPT, EXPLANATION_PROMPT, FOLLOWUP_PROMPT

load_dotenv()

# Stable model available in your account
MODEL_NAME = "openai/gpt-oss-20b"

def get_groq_client() -> Groq:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY is not configured in environment variables.")
    return Groq(api_key=api_key)

def _call_groq(prompt: str, expect_json: bool = True) -> str:
    client = get_groq_client()
    kwargs = {
        "model": MODEL_NAME,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
        "max_tokens": 600,  # Limits token consumption to prevent 429 rate limit
    }
    if expect_json:
        kwargs["response_format"] = {"type": "json_object"}
    response = client.chat.completions.create(**kwargs)
    return response.choices[0].message.content

def extract_concepts(text: str) -> list:
    if not text or not text.strip():
        return []
    raw = _call_groq(CONCEPT_EXTRACTION_PROMPT.format(text=text), expect_json=False)
    data = clean_and_parse_json(raw)
    return data if isinstance(data, list) else data.get("concepts", [])

def generate_question(text: str, topic: str, difficulty: str = "medium", question_type: str = "mcq") -> dict:
    raw = _call_groq(QUIZ_GENERATION_PROMPT.format(text=text, topic=topic, difficulty=difficulty, question_type=question_type), expect_json=True)
    data = clean_and_parse_json(raw)
    for key in ["question", "options", "correct_answer", "explanation", "topic", "difficulty", "source_page"]:
        if key not in data:
            data.setdefault(key, "N/A" if key != "source_page" else 1)
    return data

def generate_explanation(question: str, student_answer: str, correct_answer: str, source_text: str) -> str:
    return _call_groq(EXPLANATION_PROMPT.format(question=question, student_answer=student_answer, correct_answer=correct_answer, source_text=source_text), expect_json=False).strip()

def generate_followup_question(topic: str, explanation: str, difficulty: str = "easy") -> dict:
    raw = _call_groq(FOLLOWUP_PROMPT.format(topic=topic, explanation=explanation, difficulty=difficulty), expect_json=True)
    return clean_and_parse_json(raw)