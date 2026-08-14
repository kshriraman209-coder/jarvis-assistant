import hashlib
import os
import threading

from flask import Flask, jsonify, request, send_file

import brain
import config
import main as jarvis_core

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AUDIO_DIR = os.path.join(BASE_DIR, "web", "tts_cache")
os.makedirs(AUDIO_DIR, exist_ok=True)

_session_lock = threading.Lock()
_tts_lock = threading.Lock()


def synthesize(text):
    key = hashlib.md5(text.encode("utf-8")).hexdigest()
    path = os.path.join(AUDIO_DIR, f"{key}.wav")
    if os.path.exists(path):
        return path
    import pyttsx3
    # pyttsx3's SAPI driver is not thread-safe, so build a fresh engine per call.
    with _tts_lock:
        try:
            engine = pyttsx3.init()
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
    return send_file(path, mimetype="audio/wav")


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