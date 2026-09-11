QUIZ_GENERATION_PROMPT = """You are an exam designer. Generate a single {difficulty} {question_type} on the topic "{topic}".

Rules:
1. Ground the question strictly in the provided text.
2. Return ONLY a valid JSON object with the exact keys:
   - "question": string
   - "options": list of 4 strings (e.g., ["A. ...", "B. ...", "C. ...", "D. ..."])
   - "correct_answer": single letter string ("A", "B", "C", or "D")
   - "explanation": string explaining why the answer is correct
   - "topic": string
   - "difficulty": "{difficulty}"
   - "source_page": positive integer only if explicitly marked in the source, otherwise null
3. If the text cannot support the question, return {{"insufficient_source": true}}.

Source Text:
{text}
"""

EXPLANATION_PROMPT = """A student answered incorrectly. Explain simply why the correct answer is right using ONLY the source material.

Question: {question}
Student's Answer: {student_answer}
Correct Answer: {correct_answer}
Source Text: {source_text}
"""

FOLLOWUP_PROMPT = """Generate an easier follow-up question on the topic "{topic}".
Context: {explanation}
Difficulty: {difficulty}

Return ONLY a valid JSON object with keys:
- "question", "options", "correct_answer", "explanation", "topic", "difficulty", "source_page"
Use exactly four distinct options labeled A through D and a single correct_answer letter.
Use the exact requested topic and difficulty. Ground everything in the context only.
source_page must be null unless an explicit page reference supports the question.
If the context is insufficient, return {{"insufficient_source": true}}.
"""
