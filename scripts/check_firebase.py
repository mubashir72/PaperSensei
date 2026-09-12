"""Explicit live check using temporary Firebase users; never sends email."""
import secrets
import sys
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from modules import firebase_service as fb
from modules.cloud_sessions import initialize, save_workspace, load_workspace, append_message

if "--live" not in sys.argv:
    raise SystemExit("Use --live to create temporary test accounts and verify the configured Firebase project.")

accounts = []
stores = []
session_id = None
try:
    for _ in range(2):
        email = f"papersensei-check-{uuid4().hex}@example.invalid"
        password = secrets.token_urlsafe(24)
        auth = fb.authenticate(email, password, register=True)
        accounts.append(auth)
        signed_in = fb.authenticate(email, password)
        assert signed_in["uid"] == auth["uid"]
    print("PASS registration and password login")
    owner, other = accounts
    fb.fresh_token(owner, force=True)
    print("PASS token refresh")
    state = {"auth": owner}
    initialize(state)
    session_id = state["study_id"]
    store = fb.UserStore(owner)
    stores.append(store)
    state["study"]["source"] = "Temporary integration test: plants use sunlight."
    state["study"]["concepts"] = ["Photosynthesis"]
    state["study_title"] = "Temporary integration test"
    append_message(state, "user", "What do plants use?")
    append_message(state, "assistant", "Sunlight.")
    if not save_workspace(state):
        raise fb.FirebaseError(state["cloud_error"])
    load_workspace(state, session_id)
    assert len(state["chat_messages"]) == 2
    assert state["study"]["concepts"] == ["Photosynthesis"]
    rows, _ = store.list_sessions()
    assert any(row["id"] == session_id for row in rows)
    print("PASS Firestore save, list, restore, and conversation history")
    url = store.base + "/" + session_id
    response = fb._request("GET", url)
    assert response.status_code in (401, 403), "Unauthenticated access was not blocked"
    response = fb._request("GET", url, headers={"Authorization": "Bearer " + fb.fresh_token(other)})
    assert response.status_code in (401, 403), "Cross-account access was not blocked"
    response = fb._request("PATCH", url, headers={"Authorization": "Bearer " + fb.fresh_token(other)},
                           json={"fields": {"title": {"stringValue": "Unauthorized test"}}})
    assert response.status_code in (401, 403), "Cross-account write was not blocked"
    print("PASS unauthenticated and cross-account privacy")
except Exception as exc:
    if isinstance(exc, (fb.FirebaseError, AssertionError)):
        print("FAIL:", str(exc))
    else:
        print("FAIL: Unexpected response; details omitted to protect credentials.")
    sys.exitcode = 1
finally:
    clean = True
    for store in stores:
        try:
            for message in store.messages(session_id):
                response = store.request("DELETE", f"/{session_id}/messages/{message['id']}")
                clean = clean and response.ok
            response = store.request("DELETE", "/" + session_id)
            clean = clean and (response.ok or response.status_code == 404)
        except fb.FirebaseError:
            clean = False
    for auth in accounts:
        try:
            fb._auth_request("delete", {"idToken": fb.fresh_token(auth)})
        except fb.FirebaseError:
            clean = False
            print("Cleanup needed for temporary Firebase UID:", auth["uid"])
    print("PASS temporary account/data cleanup" if clean else "CHECK temporary test cleanup in Firebase Console")
    if not clean:
        sys.exitcode = 1
raise SystemExit(getattr(sys, "exitcode", 0))
