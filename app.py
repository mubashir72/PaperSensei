"""PaperSensei Streamlit entry point."""
import csv
import io
import logging
import streamlit as st
from config import MAX_SOURCE_CHARS
from modules import groq_service as ai
from modules.adaptive_engine import new_performance
from modules.document_gateway import pdf_available, read_uploaded_pdf, document_source
from modules.past_paper_analyzer import analyze_past_papers, DISCLAIMER
from modules.session_manager import new_session, set_question, submit_answer

st.set_page_config(page_title="PaperSensei", page_icon="📖", layout="wide")
if "study" not in st.session_state:
    st.session_state.study = new_session()
    st.session_state.papers = []
    st.session_state.insights = None
session = st.session_state.study


def run_action(action, message):
    try:
        with st.spinner(message):
            action()
    except (ValueError, RuntimeError) as exc:
        st.error(str(exc))
    except Exception:
        logging.getLogger(__name__).exception("PaperSensei operation failed")
        st.error("This operation could not be completed. Your saved progress is still available. Please retry.")


def start_study(source):
    if not source.strip():
        raise ValueError("Add some study material first.")
    if len(source) > MAX_SOURCE_CHARS:
        raise ValueError(f"Use at most {MAX_SOURCE_CHARS:,} characters per study section.")
    concepts = ai.extract_concepts(source)
    if not concepts:
        raise ValueError("No supported concepts were found. Try a more informative study section.")
    fresh = new_session()
    fresh.update(source=source, concepts=concepts)
    st.session_state.study = fresh
    st.rerun()


with st.sidebar:
    st.title("PaperSensei")
    st.caption("Understand. Practise. Improve.")
    screen = st.radio("Navigate", ["Home", "Documents", "Quiz", "Past paper insights", "Session summary"])
    st.divider()
    st.caption("Your progress stays in this browser session. Download your report before leaving.")
    if st.button("Reset session", width="stretch"):
        for key in list(st.session_state):
            del st.session_state[key]
        st.rerun()

if screen == "Home":
    st.title("Make your study material a personal tutor")
    st.write("Explore concepts from your notes, practise adaptive questions, and discover patterns in past papers.")
    cols = st.columns(3)
    for col, title, body in zip(cols, ["1. Add material", "2. Practise a concept", "3. See your progress"],
                               ["Use a chapter, notes, or examination papers.",
                                "Start at medium difficulty and get help when you need it.",
                                "Review strengths, weak topics, and recurring exam formats."]):
        with col:
            st.subheader(title)
            st.write(body)
    st.info("Open Documents to begin. AI features require a Groq API key configured by the app owner.")
    if not pdf_available():
        st.caption("PDF extraction is awaiting the Task 2 module. You can use pasted text now.")

elif screen == "Documents":
    st.title("Your study material")
    kind = st.radio("Document type", ["Notes / textbook", "Past paper"], horizontal=True)
    method = st.radio("Input method", ["Paste text", "Upload PDF"], horizontal=True)
    st.caption(f"Use up to {MAX_SOURCE_CHARS:,} characters per section or paper. Loading new notes starts a new quiz session.")
    if method == "Paste text":
        text = st.text_area("Source text", height=260, key="source_input")
        name = st.text_input("Document name", value="Study material")
        if st.button("Extract concepts" if kind == "Notes / textbook" else "Add past paper", type="primary"):
            def load_text():
                if not text.strip() or len(text) > MAX_SOURCE_CHARS:
                    raise ValueError(f"Enter between 1 and {MAX_SOURCE_CHARS:,} characters.")
                if kind == "Notes / textbook":
                    start_study(text)
                else:
                    paper = {"name": name.strip() or "Past paper", "text": text.strip()}
                    if paper not in st.session_state.papers:
                        st.session_state.papers.append(paper)
                        st.session_state.insights = None
                    st.success("Past paper added. Open Past paper insights to analyze it.")
            run_action(load_text, "Reading your material...")
    else:
        available = pdf_available()
        if not available:
            st.info("Your teammate's Task 2 PDF processor is not installed yet. Use Paste text to continue.")
        files = st.file_uploader("PDF documents", type=["pdf"], accept_multiple_files=kind == "Past paper", disabled=not available)
        if st.button("Load PDFs", disabled=not available or not files):
            def load_pdfs():
                selected = files if isinstance(files, list) else [files]
                docs = [read_uploaded_pdf(file) for file in selected]
                sources = [document_source(doc) for doc in docs]
                if kind == "Notes / textbook":
                    start_study(sources[0])
                else:
                    for doc, source in zip(docs, sources):
                        paper = {"name": doc["filename"], "text": source}
                        if paper not in st.session_state.papers:
                            st.session_state.papers.append(paper)
                    st.session_state.insights = None
                    st.success(f"Loaded {len(docs)} past papers.")
            run_action(load_pdfs, "Reading PDFs...")
    if session["concepts"]:
        st.subheader("Extracted concepts")
        st.write(", ".join(session["concepts"]))
        with st.expander("Current study source"):
            st.text(session["source"])
    if st.session_state.papers:
        st.subheader("Added past papers")
        for paper in st.session_state.papers:
            st.write(paper["name"])
        if st.button("Clear past papers"):
            st.session_state.papers = []
            st.session_state.insights = None
            st.rerun()

elif screen == "Quiz":
    st.title("Practise and understand")
    if not session["concepts"]:
        st.info("Add notes or a textbook section in Documents first.")
    else:
        pending = session["followup"]
        topic = st.selectbox("Concept", session["concepts"], disabled=bool(pending), key="quiz_topic")
        if pending:
            topic = pending["topic"]
            st.info(f"Let's revisit {topic} with an easier question.")
        performance = session["performance"].get(topic, new_performance(topic))
        st.caption(f'Topic level: {performance["current_difficulty"].title()} · Two consecutive correct answers raise your level; two incorrect answers lower it.')
        question = session["question"]
        can_generate = question is None or session["feedback"] is not None
        label = "Try easier follow-up" if pending else "Generate next question"
        if st.button(label, type="primary", disabled=not can_generate):
            def generate():
                if pending:
                    # Original source keeps remedial questions grounded even if the explanation API failed.
                    result = ai.generate_followup_question(topic, session["source"], pending["difficulty"])
                else:
                    result = ai.generate_question(session["source"], topic, performance["current_difficulty"], "mcq")
                set_question(session, result)
                st.rerun()
            run_action(generate, "Preparing your question...")
        if question:
            st.subheader(question["question"])
            st.caption(f'{question["topic"]} · {question["difficulty"].title()}')
            if question.get("source_page") and f'[Page {question["source_page"]}]' in session["source"]:
                st.caption(f'Source reference suggested by AI: page {question["source_page"]}')
            with st.form(f'answer_{session["question_number"]}'):
                answer = st.radio("Choose an answer", list("ABCD"),
                                  format_func=lambda x: question["options"]["ABCD".index(x)],
                                  index=None, disabled=session["feedback"] is not None)
                submitted = st.form_submit_button("Submit answer", disabled=session["feedback"] is not None)
            if submitted:
                def grade():
                    result = submit_answer(session, answer)
                    if not result["correct"]:
                        try:
                            result["explanation"] = ai.generate_explanation(
                                question["question"], question["options"]["ABCD".index(result["student_answer"])],
                                question["options"]["ABCD".index(question["correct_answer"])], session["source"])
                        except (ValueError, RuntimeError):
                            result["explanation_note"] = "The simpler explanation is unavailable; showing the original explanation."
                    st.rerun()
                run_action(grade, "Checking your answer...")
            feedback = session["feedback"]
            if feedback:
                if feedback["correct"]:
                    st.success("Correct! Keep going.")
                else:
                    st.warning(f'The correct answer is {feedback["correct_answer"]}. Review the explanation, then try the follow-up.')
                st.write(feedback["explanation"])
                if feedback.get("explanation_note"):
                    st.caption(feedback["explanation_note"])

elif screen == "Past paper insights":
    st.title("Patterns in your past papers")
    st.info(DISCLAIMER)
    papers = st.session_state.papers
    st.write(f"{len(papers)} paper(s) added.")
    if st.button("Analyze papers", type="primary", disabled=not papers):
        def analyze():
            result = analyze_past_papers([paper["text"] for paper in papers])
            st.session_state.insights = result
        run_action(analyze, "Analyzing all questions across your papers...")
    insights = st.session_state.insights
    if insights is not None:
        if not insights["topics"]:
            st.info("No examination questions were found in these papers.")
        else:
            rows = [{**row, "question_types": ", ".join(row["question_types"]),
                     "years_found": ", ".join(map(str, row["years_found"])) or "Unknown"}
                    for row in insights["topics"]]
            st.dataframe(rows, width="stretch", hide_index=True)
            st.bar_chart(rows, x="topic", y="frequency", horizontal=True)

elif screen == "Session summary":
    st.title("Your learning progress")
    history = session["history"]
    correct = sum(row["correct"] for row in history)
    cols = st.columns(3)
    cols[0].metric("Answered", len(history))
    cols[1].metric("Correct", correct)
    cols[2].metric("Accuracy", f"{correct / len(history):.0%}" if history else "—")
    if not history:
        st.info("Complete a quiz question to start tracking your progress.")
    else:
        st.dataframe(list(session["performance"].values()), hide_index=True, width="stretch")
        weak = [p["topic"] for p in session["performance"].values() if p["incorrect_count"] > p["correct_count"]]
        if weak:
            st.write("Topics to revisit: " + ", ".join(weak))
        report = io.StringIO()
        fields = ["topic", "difficulty", "question", "student_answer", "correct_answer", "correct", "explanation"]
        writer = csv.DictWriter(report, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in history:
            # Prevent source/model text from becoming spreadsheet formulas on export.
            writer.writerow({k: "'" + v if isinstance(v, str) and v.lstrip().startswith(("=", "+", "-", "@")) else v
                             for k, v in row.items()})
        st.download_button("Download quiz report", report.getvalue(), "papersensei-session.csv", "text/csv")
        with st.expander("Answer history"):
            for row in history:
                st.write(f'{row["topic"]} — {row["question"]}')
                st.caption(f'Your answer: {row["student_answer"]} | Correct answer: {row["correct_answer"]}')

