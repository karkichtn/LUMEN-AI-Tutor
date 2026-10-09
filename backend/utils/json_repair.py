import json
import re
from typing import Dict, Any, Optional

def clean_json_string(text: str) -> str:
    """Strip markdown code fence blocks, whitespace, and invalid wrapping."""
    if not text:
        return "{}"
    text = text.strip()
    # Strip markdown fence if present
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()
    return text

def parse_and_repair_json(text: str) -> Optional[Dict[str, Any]]:
    """Robustly parse JSON text, with regex-based boundary extraction and fallback."""
    cleaned = clean_json_string(text)
    
    # Direct attempt
    try:
        return json.loads(cleaned)
    except Exception:
        pass
        
    # Attempt to extract outer JSON object {...}
    match = re.search(r'(\{[\s\S]*\})', cleaned)
    if match:
        extracted = match.group(1)
        try:
            return json.loads(extracted)
        except Exception:
            pass
            
    return None
