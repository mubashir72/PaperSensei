"""Parse complete JSON only; never manufacture data from truncated output."""
import json
import re


def clean_and_parse_json(raw_text: str) -> dict | list:
    if not isinstance(raw_text, str) or not raw_text.strip():
        raise ValueError("The AI returned an empty response.")
    match = re.fullmatch(r"\s*```(?:json)?\s*([\s\S]*?)\s*```\s*", raw_text)
    try:
        data = json.loads(match.group(1) if match else raw_text)
    except json.JSONDecodeError as exc:
        raise ValueError("The AI returned incomplete or invalid JSON. Please retry.") from exc
    if not isinstance(data, (dict, list)):
        raise ValueError("Expected a JSON object or list.")
    return data
