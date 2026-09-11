QUESTION_SEGMENTATION_PROMPT = """Extract and separate individual examination questions from the provided past paper text.
Return a JSON object with a "questions" list of strings, where each string is an isolated, cleaned question statement. Include every question. Do not merge different questions.

Raw Paper Text:
{raw_text}
"""

TOPIC_CLASSIFICATION_PROMPT = """Analyze each of the following exam questions.
Classify each question into a high-level academic topic, identify its format (e.g., "MCQ", "Short question", "Long question", "Numerical problem"), and extract the examination year if clearly present.

Questions:
{questions}

Return ONLY a JSON object with a "questions" list, one entry per input question in order:
{{"questions": [
  {{
    "question": "string",
    "topic": "Normalized Topic Name",
    "question_type": "Short question",
    "year": 2024
  }}
]}}
If the year cannot be determined, return null for year.
"""
