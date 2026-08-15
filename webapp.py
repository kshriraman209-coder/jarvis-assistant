import hashlib
import os
import sys
import threading

from flask import Flask, jsonify, request, send_file

import brain
import config
import main as jarvis_core

app = Flask(__name__)

# When frozen with PyInstaller, static files live inside the bundle (--add-data)
# and the writable TTS cache goes to a user folder instead of the bundle temp dir.
if getattr(sys, "frozen", False):
    BASE_DIR = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    _cache_root = os.path.join(
        os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"),
        "JARVIS", "tts_cache",
    )
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    _cache_root = os.path.join(BASE_DIR, "web", "tts_cache")

AUDIO_DIR = _cache_root
os.makedirs(AUDIO_DIR, exist_ok=True)

_session_lock = threading.Lock()
_tts_lock = threading.Lock()


def _set_best_voice(engine):
    """Pick a voice by name preference (accent), defaulting to any available."""
    try:
        voices = engine.getProperty("voices")
        if not voices:
            return
        lowered = {v.name.lower(): v for v in voices}
        picked = None
        for name in (
            (config.TTS_VOICE_PREFERENCE,) + config.TTS_VOICE_FALLBACKS
        ):
            for key, voice in lowered.items():
                if name in key:
                    picked = voice
                    break
            if picked:
                break
        if picked is None:
            picked = voices[0]
        engine.setProperty("voice", picked.id)
    except Exception:
        pass


def _synthesize_edge(text, path):
    """Synthesize with Microsoft Edge neural TTS (human-like). MP3."""
    import asyncio
    import edge_tts
    from edge_tts import Communicate

    def _run():
        async def _inner():
            com = Communicate(text, config.TTS_EDGE_VOICE,
                              rate=config.TTS_EDGE_RATE)
            await com.save(path)
        asyncio.run(_inner())

    _run()
    return os.path.exists(path) and os.path.getsize(path) > 0


def synthesize(text, prefer_edge=True):
    key = hashlib.md5(text.encode("utf-8")).hexdigest()
    if config.TTS_ENGINE == "edge" and prefer_edge:
        path = os.path.join(AUDIO_DIR, f"{key}.mp3")
        if os.path.exists(path):
            return path
        import pyttsx3
        # Try the neural voice first; fall back to the local SAPI voice.
        with _tts_lock:
            try:
                if _synthesize_edge(text, path):
                    return path
            except Exception:
                pass
    import pyttsx3
    # pyttsx3's SAPI driver is not thread-safe, so build a fresh engine per call.
    with _tts_lock:
        try:
            path = os.path.join(AUDIO_DIR, f"{key}.wav")
            if os.path.exists(path):
                return path
            engine = pyttsx3.init()
            _set_best_voice(engine)
            engine.setProperty("rate", config.TTS_RATE)
            engine.setProperty("volume", config.TTS_VOLUME)
            engine.save_to_file(text, path)
            engine.runAndWait()
            engine.stop()
        finally:
            try:
                engine.stop()
            except Exception:
                pass
    if not os.path.exists(path):
        raise RuntimeError("TTS synthesis produced no audio")
    return path


@app.get("/api/speech")
def api_speech():
    text = request.args.get("text", "").strip()
    if not text:
        return jsonify({"error": "no text"}), 400
    path = synthesize(text)
    mime = "audio/mpeg" if path.lower().endswith(".mp3") else "audio/wav"
    return send_file(path, mimetype=mime)


@app.post("/api/chat")
def api_chat():
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()
    if not message:
        return jsonify({"reply": "I'm sorry, I didn't catch that.", "action": False}), 200

    with _session_lock:
        reply = jarvis_core.handle_command(message)
        if reply is None:
            brain.history.clear()
            reply = config.GOODBYE
        if isinstance(reply, str) and reply:
            return jsonify({"reply": reply, "action": not reply.startswith("I'm sorry,")}), 200

    return jsonify({"reply": config.UNKNOWN_REPLY, "action": False}), 200


@app.post("/api/clear")
def api_clear():
    with _session_lock:
        brain.history.clear()
    return jsonify({"cleared": True}), 200


@app.get("/api/status")
def api_status():
    ollama_ok = jarvis_core.check_ollama()
    mode = brain.current_mode()
    model = config.GEMINI_MODEL if mode == "gemini" else config.OLLAMA_MODEL
    return jsonify({
        "ollama": ollama_ok or mode == "gemini",
        "model": model,
        "mode": mode,
        "assistant": config.ASSISTANT_NAME,
        "local": mode == "ollama",
        "models": [
            {"key": "ollama", "label": f"{config.OLLAMA_MODEL} (local)"},
            {"key": "gemini", "label": f"{config.GEMINI_MODEL} (cloud)"},
        ],
    })


@app.post("/api/mode")
def api_mode():
    data = request.get_json(silent=True) or {}
    mode = (data.get("mode") or "").strip().lower()
    if mode not in ("gemini", "ollama"):
        return jsonify({"error": "mode must be 'gemini' or 'ollama'"}), 400
    current = brain.set_mode(mode)
    model = config.GEMINI_MODEL if current == "gemini" else config.OLLAMA_MODEL
    return jsonify({"mode": current, "model": model})


@app.get("/")
def index():
    return send_file(os.path.join(BASE_DIR, "web", "index.html"))


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False, threaded=True)