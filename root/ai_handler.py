import hashlib
import itertools
import os
import time

from google import genai
from dotenv import load_dotenv

load_dotenv()


MODEL = "gemini-2.5-flash"


_raw_keys = [
    os.getenv("GEMINI_API_KEY_1") or os.getenv("GEMINI_API_KEY"),
    os.getenv("GEMINI_API_KEY_2"),
    os.getenv("GEMINI_API_KEY_3"),
]
_keys    = [k.strip() for k in _raw_keys if k and k.strip()]
_clients = [genai.Client(api_key=k) for k in _keys]
_pool    = itertools.cycle(_clients)

_cache: dict = {}
CACHE_TTL = 300


def _cache_key(prompt: str) -> str:
    return hashlib.md5(prompt.encode()).hexdigest()


def ask_ai(prompt: str) -> str:
    key = _cache_key(prompt)
    if key in _cache:
        result, ts = _cache[key]
        if time.time() - ts < CACHE_TTL:
            return result

    errors = []
    for _ in range(len(_clients)):
        client = next(_pool)
        try:
            response = client.models.generate_content(model=MODEL, contents=prompt)
            text = getattr(response, "text", None)
            if isinstance(text, str) and text.strip():
                _cache[key] = (text, time.time())
                return text

            if getattr(response, "candidates", None):
                parts = []
                for candidate in response.candidates:
                    content = getattr(candidate, "content", None)
                    if not content:
                        continue
                    for part in getattr(content, "parts", []):
                        part_text = getattr(part, "text", None)
                        if isinstance(part_text, str) and part_text.strip():
                            parts.append(part_text)
                if parts:
                    result = "".join(parts)
                    _cache[key] = (result, time.time())
                    return result

        except Exception as e:
            errors.append(str(e))
            continue

    err = " | ".join(errors) if errors else "Unknown error"
    if any("quota" in e.lower() or "429" in e or "rate" in e.lower() for e in errors):
        return "All API keys have hit their rate limit. Please wait a minute and try again."
    return f"AI error: {err}"