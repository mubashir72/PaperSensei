# PaperSensei

A Streamlit tutor that turns study notes into conceptual MCQs, adapts practice to each topic, and summarizes question frequencies in uploaded past papers.

## Status and ownership

Tasks 1 and 5 implement the integrated app, adaptive engine, deterministic grading, session state, frontend, and offline regression tests. Tasks 3 and 4 were reviewed and corrected for strict response validation and complete question classification.

**Task 2 remains assigned to the PDF-processing teammate.** No PDF extractor or text-cleaning implementation is included. Paste text to exercise the application now; PDF upload automatically enables when the teammate supplies the interface below. The pre-existing `utils/text_utils.py` placeholder is untouched.

## Local setup

Use Python 3.11 or newer:

```powershell
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements-dev.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
# Set GROQ_API_KEY in .env.
.venv/Scripts/python -m streamlit run app.py
```

For macOS/Linux use `.venv/bin/python` instead. Set `GROQ_MODEL` to a model supported by your Groq account if the existing default is unavailable. Never commit API keys. On Streamlit deployments, configure `GROQ_API_KEY` in app secrets instead of a local `.env`.

## Study workflow

1. Open **Documents**, choose notes/textbook, paste an informative section, and extract concepts.
2. Open **Quiz**, choose a concept, and generate a question.
3. Submit an answer. An incorrect answer shows a simpler explanation and requires a follow-up on the same topic.
4. Add one or more past papers separately through Documents, then open **Past paper insights** and analyze them.
5. View **Session summary** and download a CSV report. Reset session clears material, questions, papers, analysis, and progress.

Each topic begins at medium. Two consecutive correct answers raise its level; two consecutive incorrect answers lower it. A pair consumes the streak, so the next level change requires another pair. Levels stay within easy/medium/hard. Every incorrect question schedules a follow-up one level below that question (easy remains easy), independent of the topic's underlying level. Follow-up answers count toward topic performance. Answer submission is locked after grading to prevent duplicate counts on rerun.

Loading new notes starts a new workspace after concept extraction succeeds and the previous workspace saves. API failures preserve existing results, and explanation failures fall back to the validated question explanation. Signed-in users can resume cloud sessions; guest progress lasts for the browser session only.

## Task 2 integration contract

Add `modules/pdf_processor.py` exposing `extract_pdf(file) -> dict`:

```python
{
    "filename": file.name,
    "total_pages": 2,
    "pages": [
        {"page_number": 1, "text": "Clean page one text"},
        {"page_number": 2, "text": "Clean page two text"},
    ],
    "full_text": "Clean page one text\nClean page two text",
}
```

The gateway accepts Streamlit UploadedFile objects, checks extension/header and the 20 MB limit, validates the returned structure, and passes explicit page markers to the tutor. Empty/scanned outputs show an OCR message. Task 2 owns actual extraction, repeated-header cleanup, chunking, and real PDF fixtures. The current gateway rejects sources over 24,000 characters instead of silently truncating them; use a smaller section until chunking is integrated. It does not claim to validate PDF internals.

## Architecture

- `app.py`: navigation, input, quizzes, insights, summary, safe report export.
- `config.py`: limits, model selection, environment/Streamlit secrets.
- `modules/adaptive_engine.py`: pure topic progression.
- `modules/session_manager.py`: session creation, questions, duplicate-safe grading.
- `modules/answer_evaluator.py`: deterministic MCQ evaluation.
- `modules/quiz_generator.py`: shared question schema validation.
- `modules/groq_service.py`: concept/question/explanation/follow-up APIs.
- `modules/document_gateway.py`: teammate PDF boundary.
- `modules/past_paper_analyzer.py`: all-question batched topic analysis.
- `prompts/`: source-grounded structured response instructions.
- `tests/`: offline service, progression, gateway, and Streamlit AppTest tests.

Groq transport uses a 30-second timeout and two SDK retries for transient errors. Malformed JSON/schema responses get one extra generation attempt and then a visible error. Incomplete JSON is never salvaged into invented records. Past-paper classification uses batches of five but processes every batch; it rejects incomplete batch results. Years are attributed only from an unambiguous paper header, never from a guessed model year. Topic normalization combines case/whitespace variants; semantic synonyms may still need review.

## Testing

```powershell
.venv/Scripts/python -m pytest -q
```

Tests mock Groq and prohibit accidental live client calls. PDF tests validate the integration boundary with fake extractor output; they do **not** certify real extraction. See `TEST_REPORT.md` for review findings, coverage, and remaining checks.

## Deployment handoff

The repository includes `requirements.txt` and `.streamlit/config.toml`. To deploy, connect this repository to Streamlit Community Cloud, select `app.py`, and add `GROQ_API_KEY` in secrets. The app can be demonstrated with pasted text before Task 2 lands.

Live hosting, GitHub branch protection/PR operations, and a demonstration recording have not been performed. Final PDF acceptance and a live Groq smoke test require the teammate's extractor and a configured API account.

## Limitations

Only MCQs are supported for quizzes. OCR, semantic topic merging, and large-document chunking are not implemented. AI output can still contain factual mistakes despite schema validation and source-grounding prompts. Past-paper frequency describes the supplied papers and does not guarantee future examination questions.

## Firebase accounts and saved conversations

The app now supports email/password registration and login, password reset, cloud quiz sessions, and source-grounded tutor chat. See [FIREBASE_SETUP.md](FIREBASE_SETUP.md) for console settings, rules, deployment configuration, data paths, and account behavior.

The local .env already contains the supplied Firebase settings. Add a Groq key separately to enable AI generation. The Python app uses Firebase REST APIs with each user's ID token; no admin private key is required. Publish firestore.rules in your Firebase Console before saving account data.
