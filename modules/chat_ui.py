"""Source-grounded chat, with retries that do not duplicate student messages."""
import streamlit as st
from modules import groq_service as ai
from modules.cloud_sessions import append_message, save_workspace


def chat_screen():
    st.title("Ask your tutor")
    source = st.session_state.study["source"]
    if not source:
        st.info("Add notes in Documents first so your tutor can answer from your study material.")
        return
    messages = st.session_state.chat_messages
    st.caption("Replies use your study material and up to 12 recent messages. Older messages remain in your history.")
    for message in messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])
    pending = bool(messages and messages[-1]["role"] == "user")
    prompt = st.chat_input("Ask about your notes…", max_chars=4000, disabled=pending)
    if prompt:
        append_message(st.session_state, "user", prompt)
        save_workspace(st.session_state)
        pending = True
    retry = st.button("Retry tutor reply") if pending and not prompt else False
    if prompt or retry:
        try:
            with st.spinner("Your tutor is thinking…"):
                answer = ai.tutor_reply(source, messages)
            append_message(st.session_state, "assistant", answer)
            save_workspace(st.session_state)
            st.rerun()
        except (ValueError, RuntimeError) as exc:
            st.error(str(exc))
            if prompt:
                st.info("Your question is retained. Reopen this screen to retry the reply.")
