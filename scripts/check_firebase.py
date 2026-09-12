"""Explicit live verification-rule check. Creates no documents and sends no emails."""
import secrets
import sys
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from modules import firebase_service as fb

if "--live" not in sys.argv:
    raise SystemExit("Use --live to check authentication and the deployed verification rule.")

auth = None
exit_code = 0
try:
    email = f"papersensei-check-{uuid4().hex}@example.invalid"
    password = secrets.token_urlsafe(24)
    auth = fb.authenticate(email, password, register=True)
    assert fb.authenticate(email, password)["uid"] == auth["uid"]
    print("PASS registration and password login")
    fb.fresh_token(auth, force=True)
    assert fb.check_email_verification(auth) is False
    print("PASS new account is unverified")
    url = fb.UserStore(auth).base + "/" + uuid4().hex
    response = fb._request("GET", url, headers={"Authorization": "Bearer " + fb.fresh_token(auth)})
    assert response.status_code == 403, "Unverified access was not denied. Publish the updated firestore.rules."
    print("PASS unverified database access denied")
    print("Verified-user saving must be checked with a verified account; no email was sent.")
except (fb.FirebaseError, AssertionError) as exc:
    print("FAIL:", str(exc))
    exit_code = 1
finally:
    if auth:
        try:
            fb._auth_request("delete", {"idToken": fb.fresh_token(auth)})
            print("PASS temporary account cleanup")
        except fb.FirebaseError:
            print("Cleanup needed for temporary Firebase UID:", auth["uid"])
            exit_code = 1
raise SystemExit(exit_code)
