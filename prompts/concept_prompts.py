CONCEPT_EXTRACTION_PROMPT = """You are an academic curriculum expert.
Extract the key concepts from the following source text.

Rules:
1. Only extract concepts explicitly covered in the text.
2. Return a JSON object with a "concepts" list of strings. Return an empty list when no academic concepts are supported.

Source Text:
{text}
"""
