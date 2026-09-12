"""Firebase REST client. All database requests use user ID tokens and Security Rules.

Never cache this client globally: its auth dictionary belongs to one Streamlit session.
"""
import json
import re
import time
from urllib.parse import quote
import requests
from config import setting


class FirebaseError(RuntimeError):
    pass


class SessionExpired(FirebaseError):
    pass


class SaveConflict(FirebaseError):
    pass


def configured():
    return bool(setting("FIREBASE_API_KEY") and setting("FIREBASE_PROJECT_ID"))


def _request(method, url, **kwargs):
    try:
        return requests.request(method, url, timeout=(5, 25), **kwargs)
    except requests.RequestException:
        # Exceptions may contain a URL with an API key. Never display/log them.
        raise FirebaseError("Firebase is unreachable. Check your connection and retry.") from None


def _auth_request(endpoint, payload):
    key = setting("FIREBASE_API_KEY")
    if not key:
        raise FirebaseError("Firebase is not configured. Add FIREBASE_API_KEY to the app settings.")
    response = _request("POST", f"https://identitytoolkit.googleapis.com/v1/accounts:{endpoint}",
                        params={"key": key}, json=payload)
    if not response.ok:
        try:
            code = response.json().get("error", {}).get("message", "").split(" : ")[0]
        except (ValueError, AttributeError):
            code = ""
        messages = {
            "EMAIL_EXISTS": "This email is already registered. Sign in instead.",
            "INVALID_EMAIL": "Enter a valid email address.",
            "WEAK_PASSWORD": "Choose a stronger password (at least six characters).",
            "INVALID_LOGIN_CREDENTIALS": "The email or password is incorrect.",
            "EMAIL_NOT_FOUND": "The email or password is incorrect.",
            "INVALID_PASSWORD": "The email or password is incorrect.",
            "USER_DISABLED": "This account has been disabled.",
            "OPERATION_NOT_ALLOWED": "Enable Email/Password in Firebase Authentication first.",
            "CONFIGURATION_NOT_FOUND": "Enable Firebase Authentication and Email/Password first.",
            "TOO_MANY_ATTEMPTS_TRY_LATER": "Too many attempts. Please try again later.",
        }
        raise FirebaseError(messages.get(code, "Firebase authentication failed. Check the project configuration and retry."))
    try:
        return response.json()
    except ValueError:
        raise FirebaseError("Firebase returned an invalid response. Please retry.") from None


def authenticate(email, password, register=False):
    email = email.strip()
    if not email or not password:
        raise FirebaseError("Enter your email and password.")
    if register and len(password) < 6:
        raise FirebaseError("Choose a password of at least six characters.")
    data = _auth_request("signUp" if register else "signInWithPassword",
                         {"email": email, "password": password, "returnSecureToken": True})
    try:
        return {"uid": data["localId"], "email": data["email"],
                "id_token": data["idToken"], "refresh_token": data["refreshToken"],
                "expires_at": time.time() + int(data["expiresIn"])}
    except (KeyError, TypeError, ValueError):
        raise FirebaseError("Firebase returned an incomplete sign-in response.") from None


def reset_password(email):
    if not email.strip():
        raise FirebaseError("Enter your email address.")
    _auth_request("sendOobCode", {"requestType": "PASSWORD_RESET", "email": email.strip()})


def load_profile(auth):
    data = _auth_request("lookup", {"idToken": fresh_token(auth)})
    users = data.get("users", [])
    if not users or users[0].get("localId") != auth["uid"]:
        raise FirebaseError("Could not load your account profile.")
    user = users[0]
    auth.update(display_name=user.get("displayName", ""), photo_url=user.get("photoUrl", ""),
                email_verified=user.get("emailVerified") is True)


def send_verification_email(auth):
    if time.time() - auth.get("verification_sent_at", 0) < 60:
        raise FirebaseError("Please wait one minute before requesting another verification email.")
    _auth_request("sendOobCode", {"requestType": "VERIFY_EMAIL", "idToken": fresh_token(auth)})
    auth["verification_sent_at"] = time.time()


def check_email_verification(auth):
    # Fail closed until both account status and refreshed token are available.
    auth["verification_ready"] = False
    load_profile(auth)
    if auth["email_verified"]:
        fresh_token(auth, force=True)
        auth["verification_ready"] = True
    auth["verification_checked_at"] = time.time()
    return auth["verification_ready"]


def update_profile(auth, name):
    name = name.strip()
    if not name or len(name) > 80:
        raise FirebaseError("Enter a name between 1 and 80 characters.")
    _auth_request("update", {"idToken": fresh_token(auth), "displayName": name, "returnSecureToken": False})
    auth["display_name"] = name


def fresh_token(auth, force=False):
    if not auth or not auth.get("uid"):
        raise SessionExpired("Sign in to access saved data.")
    if not force and auth.get("expires_at", 0) > time.time() + 60:
        return auth["id_token"]
    response = _request("POST", "https://securetoken.googleapis.com/v1/token",
                        params={"key": setting("FIREBASE_API_KEY")},
                        data={"grant_type": "refresh_token", "refresh_token": auth["refresh_token"]})
    if not response.ok:
        if response.status_code >= 500 or response.status_code == 429:
            raise FirebaseError("Firebase is temporarily unavailable. Please retry.")
        raise SessionExpired("Your login has expired. Sign out and sign in again. Unsaved work remains in this session.")
    try:
        data = response.json()
        if data["user_id"] != auth["uid"]:
            raise ValueError("User mismatch")
        token, refresh = data["id_token"], data["refresh_token"]
        expiry = time.time() + int(data["expires_in"])
    except (ValueError, KeyError, TypeError):
        raise SessionExpired("Firebase could not renew this login. Sign in again.") from None
    auth.update(id_token=token, refresh_token=refresh, expires_at=expiry)
    return token


def _segment(value):
    if not isinstance(value, str) or not value or "/" in value or value in (".", ".."):
        raise ValueError("Invalid database identifier.")
    return quote(value, safe="")


def _encode(value):
    if type(value) is int:
        return {"integerValue": str(value)}
    if isinstance(value, str):
        return {"stringValue": value}
    raise ValueError("Unsupported Firestore value.")


def _decode(document):
    result = {}
    for key, value in document.get("fields", {}).items():
        if "stringValue" in value:
            result[key] = value["stringValue"]
        elif "integerValue" in value:
            result[key] = int(value["integerValue"])
    result["id"] = document["name"].rsplit("/", 1)[-1]
    result["version"] = document.get("updateTime")
    return result


class UserStore:
    def __init__(self, auth):
        self.auth = auth
        project = setting("FIREBASE_PROJECT_ID")
        if not re.fullmatch(r"[a-z][a-z0-9-]{4,61}[a-z0-9]", project):
            raise FirebaseError("Set a valid FIREBASE_PROJECT_ID in the app settings.")
        self.base = (f"https://firestore.googleapis.com/v1/projects/{project}/databases/(default)"
                     f"/documents/users/{_segment(auth['uid'])}/study_sessions")

    def request(self, method, suffix="", **kwargs):
        for attempt in range(2):
            response = _request(method, self.base + suffix,
                                headers={"Authorization": f"Bearer {fresh_token(self.auth)}"}, **kwargs)
            if response.status_code == 401 and attempt == 0:
                fresh_token(self.auth, force=True)
                continue
            if response.status_code == 401:
                raise SessionExpired("Your login has expired. Please sign in again.")
            if response.status_code == 403:
                raise FirebaseError("Cloud access was denied. Create Firestore and publish the supplied firestore.rules for this project.")
            if response.status_code in (409, 412):
                raise SaveConflict("This study session changed in another tab. Open its saved copy or save your work as a new session.")
            return response

    def get(self, session_id):
        response = self.request("GET", "/" + _segment(session_id))
        if response.status_code == 404:
            return None
        if not response.ok:
            raise FirebaseError("Could not load this session. Check that the default Firestore database exists.")
        return _decode(response.json())

    def save(self, session_id, fields, version=None):
        params = {"currentDocument.updateTime": version} if version else {"currentDocument.exists": "false"}
        try:
            response = self.request("PATCH", "/" + _segment(session_id), params=params,
                                    json={"fields": {key: _encode(value) for key, value in fields.items()}})
        except SaveConflict:
            # A prior write may have succeeded even when its response was lost.
            remote = self.get(session_id)
            if remote and all(remote.get(key) == fields[key] for key in ("payload", "title", "schema_version")):
                return remote["version"]
            raise
        if not response.ok:
            raise FirebaseError("Could not save your session. Check Firestore setup or quota and retry.")
        return response.json()["updateTime"]

    def list_sessions(self, cursor=None):
        params = {"pageSize": 20, "orderBy": "updated_at desc",
                  "mask.fieldPaths": ["title", "updated_at", "schema_version"]}
        if cursor:
            params["pageToken"] = cursor
        response = self.request("GET", params=params)
        if not response.ok:
            raise FirebaseError("Could not list saved sessions. Create the default Firestore database and publish the rules.")
        data = response.json()
        return [_decode(doc) for doc in data.get("documents", [])], data.get("nextPageToken")

    def save_message(self, session_id, message):
        fields = {key: _encode(message[key]) for key in ("role", "content", "created_at")}
        response = self.request("PATCH", f"/{_segment(session_id)}/messages/{_segment(message['id'])}",
                                json={"fields": fields})
        if not response.ok:
            raise FirebaseError("Your message could not be saved. Retry cloud save before leaving.")

    def messages(self, session_id):
        cursor, results = None, []
        while True:
            params = {"pageSize": 100, "orderBy": "created_at asc"}
            if cursor:
                params["pageToken"] = cursor
            response = self.request("GET", f"/{_segment(session_id)}/messages", params=params)
            if not response.ok:
                raise FirebaseError("Could not load conversation history. Please retry.")
            data = response.json()
            results.extend(_decode(doc) for doc in data.get("documents", []))
            cursor = data.get("nextPageToken")
            if not cursor:
                return results
