"""Serializable study workspaces and conflict-aware cloud persistence."""
import json
from datetime import datetime, timezone
from uuid import uuid4
from modules.firebase_service import FirebaseError, UserStore
from modules.session_manager import new_session


def now():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def initialize(state):
    state.setdefault("study", new_session())
    state.setdefault("papers", [])
    state.setdefault("insights", None)
    state.setdefault("study_id", uuid4().hex)
    state.setdefault("study_title", "Untitled study session")
    state.setdefault("chat_messages", [])
    state.setdefault("cloud_version", None)
    state.setdefault("cloud_payload", None)
    state.setdefault("cloud_error", None)
    state.setdefault("message_saved_ids", [])


def payload(state):
    return json.dumps({"study": state["study"], "papers": state["papers"], "insights": state["insights"]},
                      ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def save_workspace(state):
    if not state.get("auth"):
        return True
    if not state.get("cloud_version") and not (state["study"]["source"] or state["papers"] or state["chat_messages"]):
        return True
    try:
        serialized = payload(state)
        if len(serialized.encode("utf-8")) > 750000:
            raise FirebaseError("This session is too large to save. Download your quiz report and start a smaller study session.")
        store = UserStore(state["auth"])
        saved = set(state.get("message_saved_ids", []))
        pending_messages = any(message["id"] not in saved for message in state["chat_messages"])
        if serialized != state.get("cloud_payload") or state.get("saved_title") != state["study_title"] or pending_messages:
            fields = {"title": state["study_title"][:120], "payload": serialized,
                      "updated_at": now(), "schema_version": 1}
            version = store.save(state["study_id"], fields, state.get("cloud_version"))
            state["cloud_version"] = version
            state["cloud_payload"] = serialized
            state["saved_title"] = state["study_title"]
        for message in state["chat_messages"]:
            if message["id"] not in saved:
                store.save_message(state["study_id"], message)
                saved.add(message["id"])
                state["message_saved_ids"] = sorted(saved)
        state["cloud_error"] = None
        return True
    except (FirebaseError, ValueError) as exc:
        state["cloud_error"] = str(exc)
        return False


def load_workspace(state, session_id):
    store = UserStore(state["auth"])
    document = store.get(session_id)
    if not document:
        raise FirebaseError("This saved session no longer exists.")
    try:
        data = json.loads(document["payload"])
        study = data["study"]
        if document.get("schema_version") != 1 or not isinstance(study, dict):
            raise ValueError()
        if not all(key in study for key in new_session()):
            raise ValueError()
        if not isinstance(study["source"], str) or not isinstance(study["concepts"], list):
            raise ValueError()
        if not isinstance(data["papers"], list) or not isinstance(study["history"], list):
            raise ValueError()
    except (ValueError, KeyError, TypeError):
        raise FirebaseError("This saved session has an unsupported format.") from None
    messages = store.messages(session_id)
    # Fetch and validate everything before replacing the current workspace.
    clear_workspace(state)
    state.update(study=study, papers=data["papers"], insights=data["insights"], study_id=session_id,
                 study_title=document["title"], cloud_version=document["version"],
                 cloud_payload=document["payload"], saved_title=document["title"],
                 chat_messages=messages, message_saved_ids=[m["id"] for m in messages])


def clear_workspace(state):
    # Drop widget values too, so loaded questions never inherit another session's answers.
    keep = {key: state[key] for key in ("auth", "guest") if key in state}
    for key in list(state):
        del state[key]
    state.update(keep)
    initialize(state)


def append_message(state, role, content):
    if role not in ("user", "assistant") or not isinstance(content, str) or not content.strip():
        raise ValueError("Invalid conversation message.")
    if len(content) > 30000:
        raise ValueError("The conversation message is too long to save.")
    message = {"id": uuid4().hex, "role": role, "content": content, "created_at": now()}
    state["chat_messages"].append(message)
    return message
