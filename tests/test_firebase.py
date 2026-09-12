import time
import json
import pytest
from modules import firebase_service as fb
from modules import cloud_sessions as cloud


class Response:
    def __init__(self, data=None, status=200):
        self.data = data or {}
        self.status_code = status
        self.ok = status < 400
    def json(self):
        return self.data


@pytest.fixture
def auth():
    return dict(uid="student-one", email="one@example.invalid", id_token="id-token",
                refresh_token="refresh-token", expires_at=time.time() + 3600)


def test_login_uses_firebase_and_never_stores_password(monkeypatch):
    calls = []
    def request(method, url, **kwargs):
        calls.append((method, url, kwargs))
        return Response(dict(localId="uid", email="student@example.invalid", idToken="token",
                             refreshToken="refresh", expiresIn="3600"))
    monkeypatch.setattr(fb, "_request", request)
    monkeypatch.setenv("FIREBASE_API_KEY", "fake-api-key")
    user = fb.authenticate(" student@example.invalid ", "password")
    assert user["uid"] == "uid"
    assert "password" not in user
    assert calls[0][1].endswith("accounts:signInWithPassword")
    assert calls[0][2]["json"]["email"] == "student@example.invalid"
    fb.authenticate("student@example.invalid", "password", register=True)
    assert calls[1][1].endswith("accounts:signUp")


@pytest.mark.parametrize("code", ["INVALID_LOGIN_CREDENTIALS", "OPERATION_NOT_ALLOWED", "CONFIGURATION_NOT_FOUND", "EMAIL_EXISTS"])
def test_auth_errors_are_safe(monkeypatch, code):
    monkeypatch.setenv("FIREBASE_API_KEY", "fake-api-key")
    monkeypatch.setattr(fb, "_request", lambda *a, **k: Response({"error": {"message": code}}, 400))
    with pytest.raises(fb.FirebaseError) as exc:
        fb.authenticate("one@example.invalid", "private-password")
    assert "private-password" not in str(exc.value)
    assert "fake-api-key" not in str(exc.value)


def test_password_reset(monkeypatch):
    calls = []
    monkeypatch.setattr(fb, "_auth_request", lambda e, p: calls.append((e, p)))
    fb.reset_password("student@example.invalid")
    assert calls == [("sendOobCode", {"requestType": "PASSWORD_RESET", "email": "student@example.invalid"})]


def test_load_and_update_profile(monkeypatch, auth):
    calls = []
    def request(endpoint, payload):
        calls.append((endpoint, payload))
        return {"users": [{"localId": auth["uid"], "displayName": "Student", "photoUrl": "https://example.com/avatar.png"}]}
    monkeypatch.setattr(fb, "_auth_request", request)
    fb.load_profile(auth)
    assert auth["display_name"] == "Student"
    assert auth["photo_url"] == "https://example.com/avatar.png"
    fb.update_profile(auth, " New Name ")
    assert auth["display_name"] == "New Name"
    assert calls[-1][1]["displayName"] == "New Name"
    with pytest.raises(fb.FirebaseError):
        fb.update_profile(auth, " ")


def test_token_refresh_and_user_mismatch(monkeypatch, auth):
    auth["expires_at"] = 0
    monkeypatch.setattr(fb, "_request", lambda *a, **k: Response({
        "user_id": "student-one", "id_token": "new", "refresh_token": "new-refresh", "expires_in": "3600"}))
    assert fb.fresh_token(auth) == "new"
    assert auth["refresh_token"] == "new-refresh"
    monkeypatch.setattr(fb, "_request", lambda *a, **k: Response({
        "user_id": "someone-else", "id_token": "bad", "refresh_token": "bad", "expires_in": "3600"}))
    with pytest.raises(fb.SessionExpired):
        fb.fresh_token(auth, force=True)
    assert auth["id_token"] == "new"


def test_http_requests_are_user_scoped(monkeypatch, auth):
    monkeypatch.setenv("FIREBASE_PROJECT_ID", "papersensei-test")
    calls = []
    def request(method, url, **kwargs):
        calls.append((url, kwargs))
        return Response({"documents": [], "nextPageToken": "page2"})
    monkeypatch.setattr(fb, "_request", request)
    assert fb.UserStore(auth).list_sessions() == ([], "page2")
    assert calls[0][0].endswith("/users/student-one/study_sessions")
    assert calls[0][1]["headers"] == {"Authorization": "Bearer id-token"}
    assert "payload" not in calls[0][1]["params"]["mask.fieldPaths"]


@pytest.mark.parametrize("value", ["../other", "user/session", "", ".."])
def test_path_escape_rejected(value):
    with pytest.raises(ValueError):
        fb._segment(value)


def test_permission_denied(monkeypatch, auth):
    monkeypatch.setenv("FIREBASE_PROJECT_ID", "papersensei-test")
    monkeypatch.setattr(fb, "_request", lambda *a, **k: Response(status=403))
    with pytest.raises(fb.FirebaseError, match="publish"):
        fb.UserStore(auth).list_sessions()


def test_conflict_does_not_overwrite(monkeypatch, auth):
    monkeypatch.setenv("FIREBASE_PROJECT_ID", "papersensei-test")
    store = fb.UserStore(auth)
    monkeypatch.setattr(store, "request", lambda *a, **k: (_ for _ in ()).throw(fb.SaveConflict("conflict")))
    monkeypatch.setattr(store, "get", lambda sid: {"payload": "other user's tab data"})
    with pytest.raises(fb.SaveConflict):
        store.save("session", {"payload": "mine", "title": "title", "schema_version": 1}, "version1")


class FakeStore:
    documents = {}
    message_rows = {}
    writes = 0
    fail = False

    def __init__(self, auth):
        self.uid = auth["uid"]
    def save(self, sid, fields, version=None):
        if self.fail:
            raise fb.FirebaseError("Offline")
        type(self).writes += 1
        version = str(self.writes)
        self.documents[(self.uid, sid)] = {**fields, "id": sid, "version": version}
        return version
    def get(self, sid):
        return self.documents.get((self.uid, sid))
    def save_message(self, sid, message):
        self.message_rows[(self.uid, sid, message["id"])] = dict(message)
    def messages(self, sid):
        return [dict(v) for (uid, session, mid), v in self.message_rows.items() if uid == self.uid and session == sid]
    def list_sessions(self, cursor=None):
        return [v for (uid, sid), v in self.documents.items() if uid == self.uid], None


@pytest.fixture
def store(monkeypatch):
    FakeStore.documents = {}
    FakeStore.message_rows = {}
    FakeStore.writes = 0
    FakeStore.fail = False
    monkeypatch.setattr(cloud, "UserStore", FakeStore)
    return FakeStore


def test_save_load_messages_and_no_rerun_writes(store, auth):
    state = {"auth": auth}
    cloud.initialize(state)
    state["study"]["source"] = "Plants use sunlight."
    state["study"]["concepts"] = ["Photosynthesis"]
    cloud.append_message(state, "user", "Explain photosynthesis")
    cloud.append_message(state, "assistant", "Plants use sunlight to make food.")
    assert cloud.save_workspace(state)
    sid = state["study_id"]
    assert cloud.save_workspace(state)
    assert store.writes == 1
    assert len(store.message_rows) == 2
    cloud.clear_workspace(state)
    assert state["auth"] == auth
    cloud.load_workspace(state, sid)
    assert state["study"]["source"] == "Plants use sunlight."
    assert len(state["chat_messages"]) == 2
    assert "refresh_token" not in json.dumps(store.documents[(auth["uid"], sid)])


def test_save_failure_retains_work(store, auth):
    state = {"auth": auth}
    cloud.initialize(state)
    state["study"]["source"] = "Unsaved notes"
    store.fail = True
    assert not cloud.save_workspace(state)
    assert state["study"]["source"] == "Unsaved notes"
    assert state["cloud_payload"] is None
    assert state["cloud_error"] == "Offline"
    store.fail = False
    assert cloud.save_workspace(state)
    assert state["cloud_error"] is None


def test_failed_load_does_not_replace_current_state(store, auth):
    state = {"auth": auth}
    cloud.initialize(state)
    state["study"]["source"] = "Current notes"
    store.documents[(auth["uid"], "broken")] = {"payload": "bad-json", "schema_version": 1}
    with pytest.raises(fb.FirebaseError):
        cloud.load_workspace(state, "broken")
    assert state["study"]["source"] == "Current notes"


def test_guest_never_saves(store):
    state = {"guest": True}
    cloud.initialize(state)
    state["study"]["source"] = "Guest notes"
    assert cloud.save_workspace(state)
    assert store.writes == 0

def test_verification_api_refreshes_only_after_verified(monkeypatch, auth):
    monkeypatch.setattr(fb, "load_profile", lambda a: a.update(email_verified=False))
    calls = []
    monkeypatch.setattr(fb, "fresh_token", lambda a, force=False: calls.append(force) or "renewed")
    assert fb.check_email_verification(auth) is False
    assert calls == []
    monkeypatch.setattr(fb, "load_profile", lambda a: a.update(email_verified=True))
    assert fb.check_email_verification(auth) is True
    assert calls == [True]


def test_verification_email_and_cooldown(monkeypatch, auth):
    calls = []
    monkeypatch.setattr(fb, "_auth_request", lambda e, p: calls.append((e, p)))
    fb.send_verification_email(auth)
    assert calls == [("sendOobCode", {"requestType": "VERIFY_EMAIL", "idToken": "id-token"})]
    with pytest.raises(fb.FirebaseError, match="one minute"):
        fb.send_verification_email(auth)
    assert len(calls) == 1


def test_verification_refresh_failure_stays_blocked(monkeypatch, auth):
    monkeypatch.setattr(fb, "load_profile", lambda a: a.update(email_verified=True))
    def fail(*a, **k):
        raise fb.FirebaseError("Network unavailable")
    monkeypatch.setattr(fb, "fresh_token", fail)
    with pytest.raises(fb.FirebaseError):
        fb.check_email_verification(auth)
    assert auth["verification_ready"] is False
