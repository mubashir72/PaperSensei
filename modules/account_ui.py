"""Streamlit account gate and saved-session browser."""
import streamlit as st
import time
from modules.firebase_service import FirebaseError, configured, authenticate, reset_password, UserStore
from modules.cloud_sessions import initialize, save_workspace, load_workspace, clear_workspace
from modules.firebase_service import load_profile, update_profile
from modules.firebase_service import send_verification_email, check_email_verification
from modules.ui_style import avatar


def verification_gate(auth):
    error = None
    if time.time() - auth.get("verification_checked_at", 0) >= 300:
        try:
            check_email_verification(auth)
        except FirebaseError as exc:
            error = str(exc)
    if auth.get("verification_ready"):
        return
    st.title("Verify your email")
    st.write("Open the verification link in your email, then return here to continue.")
    st.text(auth["email"])
    st.caption("Check your spam folder too. Your saved sessions will be available after verification.")
    if error or auth.get("verification_send_error"):
        st.error(error or auth["verification_send_error"])
    if auth.get("verification_sent_at"):
        st.success("Verification email requested. Check your inbox for the link.")
    if st.button("I've verified my email", type="primary"):
        try:
            if check_email_verification(auth):
                st.rerun()
            st.warning("Your email is not verified yet. Click the link in the email and try again.")
        except FirebaseError as exc:
            st.error(str(exc))
    if st.button("Resend verification email"):
        try:
            send_verification_email(auth)
            auth.pop("verification_send_error", None)
            st.rerun()
        except FirebaseError as exc:
            st.error(str(exc))
    st.caption("You can request another email once per minute.")
    if st.button("Sign out"):
        st.session_state.clear()
        st.rerun()
    st.stop()


def account_gate():
    initialize(st.session_state)
    if st.session_state.get("auth"):
        verification_gate(st.session_state.auth)
        return
    if st.session_state.get("guest"):
        return
    st.title("Welcome to PaperSensei")
    st.write("Sign in to save your quizzes, study material, and tutor conversations.")
    if not configured():
        st.info("Account login is not configured yet. You can still preview the app.")
    else:
        mode = st.radio("Account action", ["Sign in", "Create account", "Reset password"], horizontal=True)
        with st.form("account_form", clear_on_submit=True):
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password", key="login_password") if mode != "Reset password" else ""
            confirmation = st.text_input("Confirm password", type="password") if mode == "Create account" else password
            submitted = st.form_submit_button(mode, type="primary")
        if submitted:
            try:
                if mode == "Reset password":
                    reset_password(email)
                    st.success("Password reset requested. Check your email for instructions.")
                else:
                    if confirmation != password:
                        raise FirebaseError("The passwords do not match.")
                    auth = authenticate(email, password, register=mode == "Create account")
                    # No other user's or guest's data is inherited on login.
                    st.session_state.clear()
                    st.session_state.auth = auth
                    initialize(st.session_state)
                    if mode == "Create account":
                        try:
                            send_verification_email(auth)
                        except FirebaseError as exc:
                            auth["verification_send_error"] = str(exc)
                    st.rerun()
            except FirebaseError as exc:
                st.error(str(exc))
    if st.button("Preview without an account"):
        st.session_state.guest = True
        st.rerun()
    st.caption("Passwords are sent to Firebase for authentication and are never stored in the study database. You may need to sign in again after reopening the app.")
    st.stop()


def account_sidebar():
    auth = st.session_state.get("auth")
    if auth:
        if not auth.get("profile_checked"):
            try:
                load_profile(auth)
            except FirebaseError:
                pass  # Login and studying remain available during a profile outage.
            auth["profile_checked"] = True
        picture, menu = st.columns([1, 4], vertical_alignment="center")
        with picture:
            avatar(auth)
        with menu:
            with st.popover("My profile", icon=":material/account_circle:", width="stretch"):
                avatar(auth)
                st.subheader(auth.get("display_name") or "Your profile")
                st.text(auth["email"])
                st.caption("Personal learning account")
                with st.form("profile_details"):
                    name = st.text_input("Display name", value=auth.get("display_name", ""), max_chars=80,
                                         placeholder="What should we call you?")
                    if st.form_submit_button("Save profile"):
                        try:
                            update_profile(auth, name)
                            st.rerun()
                        except FirebaseError as exc:
                            st.error(str(exc))
                if not auth.get("photo_url"):
                    st.caption("Your account has no profile photo. Google photos are available for accounts connected through Google sign-in.")
                if st.button("Refresh profile"):
                    try:
                        load_profile(auth)
                        st.rerun()
                    except FirebaseError as exc:
                        st.error(str(exc))
                st.divider()
                if st.button("Sign out", width="stretch", icon=":material/logout:"):
                    if save_workspace(st.session_state):
                        st.session_state.clear()
                        st.rerun()
                if st.session_state.get("cloud_error"):
                    if st.button("Sign out and discard unsaved changes"):
                        st.session_state.clear()
                        st.rerun()
    else:
        st.caption("Guest preview: progress lasts for this browser session.")
        if st.button("Go to sign in"):
            st.session_state.clear()
            st.rerun()


def saved_sessions_screen():
    st.title("My saved sessions")
    if not st.session_state.get("auth"):
        st.info("Sign in to save and resume your study sessions.")
        return
    st.caption("Open a session to restore its notes, quiz, topic progress, papers, and conversation.")
    if st.button("Refresh saved sessions") or "saved_rows" not in st.session_state:
        try:
            rows, cursor = UserStore(st.session_state.auth).list_sessions()
            st.session_state.saved_rows = rows
            st.session_state.saved_cursor = cursor
        except FirebaseError as exc:
            st.error(str(exc))
            return
    rows = st.session_state.get("saved_rows", [])
    if not rows:
        st.info("No saved sessions yet. Add study material to begin.")
    for row in rows:
        left, right = st.columns([4, 1])
        left.write(row.get("title", "Study session"))
        left.caption(row.get("updated_at", ""))
        if right.button("Open", key=f'open_{row["id"]}'):
            if save_workspace(st.session_state):
                try:
                    load_workspace(st.session_state, row["id"])
                    st.rerun()
                except FirebaseError as exc:
                    st.error(str(exc))
    if st.session_state.get("saved_cursor") and st.button("Load more sessions"):
        try:
            rows, cursor = UserStore(st.session_state.auth).list_sessions(st.session_state.saved_cursor)
            st.session_state.saved_rows.extend(rows)
            st.session_state.saved_cursor = cursor
            st.rerun()
        except FirebaseError as exc:
            st.error(str(exc))
