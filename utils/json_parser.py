import json
import re

def clean_and_parse_json(raw_text: str) -> dict | list:
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw_text)
    clean_str = match.group(1).strip() if match else raw_text.strip()
    return json.loads(clean_str)