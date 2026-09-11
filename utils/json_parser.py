import json
import re

def clean_and_parse_json(raw_text: str) -> dict | list:
    """Extracts and parses JSON, with regex fallback for truncated LLM responses."""
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw_text)
    clean_str = match.group(1).strip() if match else raw_text.strip()
    
    try:
        return json.loads(clean_str)
    except json.JSONDecodeError:
        # Fallback: Agar array truncate ho gaya ho, to complete elements recover karein
        objects = re.findall(r"\{[^{}]*\}", clean_str)
        recovered = []
        for obj in objects:
            try:
                recovered.append(json.loads(obj))
            except Exception:
                continue
        if recovered:
            return recovered
        # Agar list of strings truncate hui ho
        strings = re.findall(r'"([^"\\]*(?:\\.[^"\\]*)*)"', clean_str)
        if strings:
            return strings
        return []