import requests
from config import (
    OLLAMA_HOST, OLLAMA_MODEL, OLLAMA_STREAM, OLLAMA_CTX, OLLAMA_KEEP_ALIVE,
    PROVIDER, GEMINI_API_KEY, GEMINI_MODEL, GEMINI_URL,
)

SYSTEM_PROMPT = (
    "You are J.A.R.V.I.S., an intelligent personal assistant in the style of "
    "the AI from Iron Man. You are helpful, precise, polite, and calm. "
    "Always address the user as 'sir'. Keep responses brief (under 40 words) "
    "unless the user asks for detail."
)

history = []
MAX_HISTORY = 20

# Cache: None=unknown, True/Gemini, False/Ollama
_mode = None
_forced = None  # runtime override set from the web UI (None = use config)


def current_mode():
    """Return the provider actually in use: 'gemini' or 'ollama'."""
    global _mode
    if _forced is not None:
        return _forced
    if _mode is None:
        if PROVIDER == "gemini":
            _mode = "gemini" if GEMINI_API_KEY else "ollama"
        else:
            _mode = "ollama"
    return _mode


def set_mode(mode):
    """Switch the active provider at runtime ('gemini' | 'ollama')."""
    global _forced
    if mode in ("gemini", "ollama"):
        _forced = mode
    return current_mode()


def _ask_gemini(prompt):
    messages = [{"role": "user", "content": SYSTEM_PROMPT + "\n\nThe user's first message follows."}]
    messages.append({"role": "user", "content": prompt})

    url = GEMINI_URL.format(model=GEMINI_MODEL, key=GEMINI_API_KEY)
    payload = {"contents": [{"parts": [{"text": m["content"]}]} for m in messages]}
    resp = requests.post(url, json=payload, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    candidates = data.get("candidates") or []
    if not candidates:
        return ""
    parts = candidates[0].get("content", {}).get("parts") or []
    return "".join(p.get("text", "") for p in parts).strip()


def _ask_ollama(prompt):
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(history[-MAX_HISTORY:])
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": OLLAMA_STREAM,
        "options": {"num_ctx": OLLAMA_CTX},
        "keep_alive": OLLAMA_KEEP_ALIVE,
    }
    resp = requests.post(
        f"{OLLAMA_HOST}/api/chat",
        json=payload,
        timeout=180,
    )
    resp.raise_for_status()
    data = resp.json()
    return data.get("message", {}).get("content", "").strip()


def ask(prompt):
    if current_mode() == "gemini":
        try:
            reply = _ask_gemini(prompt)
        except Exception:
            # Fall back to local Ollama if the cloud call fails.
            reply = _ask_ollama(prompt)
    else:
        reply = _ask_ollama(prompt)

    if reply:
        history.append({"role": "user", "content": prompt})
        history.append({"role": "assistant", "content": reply})
    return reply