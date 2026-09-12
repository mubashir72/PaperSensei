# Review and test report

## Scope

Implemented Tasks 1 and 5 after reviewing the supplied Task 3 and Task 4 code. Task 2 extraction and cleaning remain with the teammate. The original untracked text-utils placeholder was preserved.

## Reviewed issues and fixes

| Finding and reproduction | Expected behavior | Resolution |
| --- | --- | --- |
| Return an incomplete question object from Groq; missing fields become "N/A". | Unusable questions must not reach the quiz. | Shared schema validation, one regeneration attempt, then a visible error. |
| Supply truncated JSON; the parser recovers unrelated strings/objects. | Reject incomplete responses. | Strict JSON parsing; complete fenced JSON remains supported. |
| Analyze a paper with seven questions. Only the first five were classified. | Count every segmented question. | Process all questions in five-item batches and require complete classification. |
| Put a year in the paper header only. Segmentation loses it. | Preserve reliable paper-level year context. | Attribute one unambiguous header year; unknown or ambiguous years stay unknown. |
| Run the old tests without a Groq key. | Offline regression tests should be reproducible. | Mocked service responses and a fixture that blocks live client calls. |

## Verification

The complete offline suite passed **51 tests** on Windows with Python 3.14.5, Streamlit 1.58.0, Groq 1.7.0, and pytest 9.1.1.

Coverage includes:

- Correct and incorrect grading at easy, medium, and hard levels.
- Two-answer progression, level bounds, interrupted streaks, topic independence, and reset.
- Same-topic remedial questions and duplicate-submission protection.
- Missing API keys, Streamlit secrets, malformed JSON, incomplete schemas, truncation, source limits, and retry exhaustion.
- Single and multiple papers, more than five questions, percentages, normalization, year attribution, and incomplete classifications.
- Upload boundary checks for empty, invalid, oversized, and non-PDF files; mocked readable/scanned extraction outputs and invalid page references.
- Streamlit concept extraction, quiz generation, wrong-answer explanation, easier follow-up, correct answer, summary, reset, errors, and insights.

An initial UI run exceeded AppTest's default three-second startup limit while loading the summary; isolated and full reruns passed. AppTest now allows ten seconds for slower startup environments.

Run: `.venv/Scripts/python -m pytest -q`

## Remaining acceptance checks

These are not certified by mocked tests:

- Task 2 must supply the extractor plus real valid, empty, scanned, corrupt, and large PDF fixtures. Verify page preservation and cleaning against those PDFs.
- Configure a real Groq key and run the sample notes and two sample papers. Check factual grounding, actual account model availability, and response quality.
- Hosting has not been published. Deployment instructions and offline GitHub Actions configuration are included; the cloud run itself is unverified.
- AI topic synonyms may remain separate. Historical frequency never guarantees future questions.
- A demonstration recording and presentation are not code deliverables and have not been produced.

## Demonstration

Paste `tests/sample_data/biology_notes.txt` into Documents and extract concepts. Generate a medium MCQ, answer incorrectly, read the explanation, and answer the easier follow-up. Add each sample paper separately, analyze the two papers, then inspect and download the session report.


## Firebase integration verification on September 12, 2026

The account integration suite passes 72 offline tests, including registration/login errors, password reset, token renewal, user-scoped requests, path validation, save conflicts, message persistence, save failure recovery, guest isolation, and Streamlit login/chat/restore/logout flows.

A live test against the configured papersensei-ba4b3 Firebase project passed:

- Temporary account registration and password login.
- ID token renewal.
- Firestore save, session listing, workspace restore, and conversation history.
- Denial of unauthenticated reads and cross-account reads/writes.
- Removal of all temporary test data and accounts.

The local Firebase configuration is in the ignored .env file. Firestore rules were reported published by the user and their account-isolation behavior was verified by the live check. No service-account private key is used.

Groq-backed content generation still requires GROQ_API_KEY; it was not live-tested as part of Firebase verification. Task 2 remains unchanged.

## Email verification update

77 offline tests pass, including verification gating, email request cooldown, verification status checks, token renewal, and failure handling. No real verification emails were sent by the automated tests. The stricter rules require publishing in Firebase Console; live verified-user access should be checked after the owner verifies an account.

## Task 2 completion
Implemented real PDF extraction, page references, repeated-margin cleanup, source sections, and PDF preview/selection. The suite passed 87 tests; an additional PDF-to-study UI test also passed (88 tests overall). Scanned PDFs require OCR and remain unsupported. Large papers require selecting a section containing complete questions. Raw PDFs are not stored in Firebase.
