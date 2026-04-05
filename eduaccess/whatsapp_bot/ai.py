# whatsapp_bot/ai.py
import json
import os
from pathlib import Path
from urllib import error, request

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env", override=True)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")


def _extract_text(response_data):
    candidates = response_data.get("candidates", [])
    for candidate in candidates:
        content = candidate.get("content", {})
        parts = content.get("parts", [])
        text_chunks = [part.get("text", "") for part in parts if part.get("text")]
        if text_chunks:
            return "".join(text_chunks).strip()
    return ""


def _call_gemini(user_prompt, system_prompt=None):
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not set.")

    contents = []
    if system_prompt:
        contents.append(
            {
                "role": "user",
                "parts": [{"text": f"System instruction: {system_prompt}"}],
            }
        )
    contents.append({"role": "user", "parts": [{"text": user_prompt}]})

    payload = {"contents": contents}
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    )
    req = request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=30) as response:
            response_data = json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Gemini API error {exc.code}: {error_body}"
        ) from exc
    except error.URLError as exc:
        raise RuntimeError(f"Gemini network error: {exc.reason}") from exc

    text = _extract_text(response_data)
    if not text:
        raise RuntimeError(f"Gemini returned no text: {response_data}")
    return text


def ask_ai(question):
    return _call_gemini(question, system_prompt="You are a helpful tutor.")


def generate_question():
    text = _call_gemini(
        "Create one question and provide the answer separately.",
        system_prompt="Generate a simple secondary school question with answer.",
    )
    parts = text.split("Answer:")
    question = parts[0].strip()
    answer = parts[1].strip() if len(parts) > 1 else "unknown"
    return question, answer
