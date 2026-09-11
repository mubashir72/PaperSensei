CONCEPT_EXTRACTION_PROMPT = """You are an academic curriculum expert.
Extract the key concepts from the following source text.

Rules:
1. Only extract concepts explicitly covered in the text.
2. Return a pure JSON list of strings (e.g. ["Concept 1", "Concept 2"]).

Source Text:
{text}
"""