"""Application settings; secrets are resolved only when a client is needed."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

MODEL_NAME = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
MAX_SOURCE_CHARS = 24000
MAX_UPLOAD_BYTES = 20 * 1024 * 1024
DIFFICULTIES = ("easy", "medium", "hard")


def setting(name, default=""):
    value = os.getenv(name)
    if value is not None:
        return value.strip()
    try:
        import streamlit as st
        return str(st.secrets.get(name, default)).strip()
    except (FileNotFoundError, RuntimeError):
        return default


def get_api_key():
    key = os.getenv("GROQ_API_KEY", "").strip()
    if not key:
        try:
            import streamlit as st
            key = str(st.secrets.get("GROQ_API_KEY", "")).strip()
        except (FileNotFoundError, RuntimeError):
            pass
    if not key:
        raise ValueError("Set GROQ_API_KEY in .env or Streamlit secrets before using AI features.")
    return key
