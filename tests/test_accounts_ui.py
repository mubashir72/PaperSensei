from pathlib import Path
from streamlit.testing.v1 import AppTest
from modules import account_ui, cloud_sessions, groq_service as ai
from tests.test_app import click, navigate
from tests.test_firebase import FakeStore


def fake_services(monkeypatch):
    monkeypatch.setattr(account_ui, "load_profile", lambda auth: auth.update(display_name="Test Student", photo_url=""))
    FakeStore.documents = {}
    FakeStore.message_rows = {}
    FakeStore.writes = 0
    FakeStore.fail = False
    monkeypatch.setattr(account_ui, "configured", lambda: True)
    monkeypatch.setattr(account_ui, "authenticate", lambda *a, **k: {
        "uid": "one", "email": "one@example.invalid", "id_token": "test", "refresh_token": "test"})
    monkeypatch.setattr(account_ui, "UserStore", FakeStore)
    monkeypatch.setattr(cloud_sessions, "UserStore", FakeStore)


def login(app):
    next(t for t in app.text_input if t.label == "Email").set_value("one@example.invalid")
    next(t for t in app.text_input if t.label == "Password").set_value("secret123")
    click(app, "Sign in")


def test_login_chat_save_restore_logout(monkeypatch):
    fake_services(monkeypatch)
    monkeypatch.setattr(ai, "extract_concepts", lambda text: ["Photosynthesis"])
    monkeypatch.setattr(ai, "tutor_reply", lambda source, messages: "Plants use sunlight.")
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / "app.py", default_timeout=10).run()
    assert app.title[0].value == "Welcome to PaperSensei"
    login(app)
    navigate(app, "Documents")
    app.text_area[0].set_value("Plants use sunlight.")
    click(app, "Extract concepts")
    sid = app.session_state["study_id"]
    navigate(app, "Tutor chat")
    app.chat_input[0].set_value("Explain this.").run()
    assert len(app.chat_message) == 2
    assert len(FakeStore.message_rows) == 2
    click(app, "Reset session")
    assert app.session_state["auth"]["uid"] == "one"
    navigate(app, "My saved sessions")
    click(app, "Open")
    assert app.session_state["study_id"] == sid
    navigate(app, "Tutor chat")
    assert len(app.chat_message) == 2
    click(app, "Sign out")
    assert app.title[0].value == "Welcome to PaperSensei"
    assert app.session_state["chat_messages"] == []
    assert app.session_state["study"]["source"] == ""
    assert not app.exception


def test_login_error(monkeypatch):
    fake_services(monkeypatch)
    from modules.firebase_service import FirebaseError
    def fail(*a, **k):
        raise FirebaseError("The email or password is incorrect.")
    monkeypatch.setattr(account_ui, "authenticate", fail)
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / "app.py", default_timeout=10).run()
    login(app)
    assert app.error
    assert not app.session_state.filtered_state.get("auth")
    assert not app.exception


def test_failed_save_blocks_logout(monkeypatch):
    fake_services(monkeypatch)
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / "app.py", default_timeout=10).run()
    login(app)
    app.session_state["study"]["source"] = "Important work"
    FakeStore.fail = True
    click(app, "Sign out")
    assert app.session_state["auth"]["uid"] == "one"
    assert app.session_state["study"]["source"] == "Important work"
    assert app.error
    click(app, "Sign out and discard unsaved changes")
    assert app.title[0].value == "Welcome to PaperSensei"
    assert not app.exception
