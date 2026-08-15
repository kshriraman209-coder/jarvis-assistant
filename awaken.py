"""
awaken.py — background wake-word launcher.

Runs silently in the background, listens for the wake word ("jarvis"),
and when it hears it: ensures Ollama + the web app are running and opens
the web app in the browser.

Run once at login (or double-click) and forget it.
"""

import os
import shutil
import subprocess
import sys
import threading
import webbrowser
import time

import pyttsx3
import requests
import speech_recognition as sr

import config

HERE = os.path.dirname(os.path.abspath(__file__))
WEB_URL = "http://127.0.0.1:5000"

_tts = None


def _init_tts():
    global _tts
    try:
        _tts = pyttsx3.init()
        _tts.setProperty("rate", config.TTS_RATE)
        _tts.setProperty("volume", config.TTS_VOLUME)
    except Exception:
        _tts = None


def _speak(text):
    if _tts:
        t = threading.Thread(target=lambda: (_tts.say(text), _tts.runAndWait()))
        t.daemon = True
        t.start()


def _is_up(url, timeout=3):
    try:
        return requests.get(url, timeout=timeout).status_code == 200
    except Exception:
        return False


def _start_ollama():
    exe = shutil.which("ollama")
    if not exe:
        cand = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Ollama", "ollama.exe")
        if os.path.isfile(cand):
            exe = cand
    if exe:
        try:
            subprocess.Popen([exe, "serve"],
                             creationflags=subprocess.CREATE_NO_WINDOW)
        except Exception:
            pass


def ensure_ollama():
    if _is_up(f"{config.OLLAMA_HOST}/api/tags"):
        return True
    _start_ollama()
    for _ in range(20):
        if _is_up(f"{config.OLLAMA_HOST}/api/tags"):
            return True
        time.sleep(0.5)
    return False


def _start_webapp():
    try:
        log = os.path.join(os.environ.get("TEMP", "."), "jarvis_web.log")
        err = os.path.join(os.environ.get("TEMP", "."), "jarvis_web_err.log")
        subprocess.Popen(
            [sys.executable, "-u", os.path.join(HERE, "webapp.py")],
            cwd=HERE,
            creationflags=subprocess.CREATE_NO_WINDOW,
            stdout=open(log, "w"), stderr=open(err, "w"),
        )
    except Exception:
        pass


def ensure_webapp():
    if _is_up(WEB_URL + "/api/status"):
        return True
    _start_webapp()
    for _ in range(20):
        if _is_up(WEB_URL + "/api/status"):
            return True
        time.sleep(0.5)
    return False


def boot():
    # Open the browser IMMEDIATELY so the page starts loading right away.
    webbrowser.open(WEB_URL)
    _speak("Yes, sir? Opening the web app.")

    # Bring everything up in parallel in the background — no blocking waits.
    t1 = threading.Thread(target=ensure_ollama, daemon=True)
    t2 = threading.Thread(target=ensure_webapp, daemon=True)
    t1.start()
    t2.start()


def wake_detected(transcript):
    low = transcript.lower()
    return any(w in low for w in config.WAKE_WORDS)


def listen_loop():
    recognizer = sr.Recognizer()
    recognizer.energy_threshold = config.MIC_ENERGY_THRESHOLD
    recognizer.dynamic_energy_threshold = True
    recognizer.pause_threshold = config.MIC_PAUSE_THRESHOLD
    errors = 0
    while True:
        audio = None
        try:
            with sr.Microphone(device_index=config.MIC_DEVICE_INDEX) as source:
                recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = recognizer.listen(source, timeout=60, phrase_time_limit=5)
        except sr.WaitTimeoutError:
            continue
        except Exception as e:
            errors += 1
            print(f"[MIC ERROR ({errors})] {e}")
            if errors >= 5:
                print("[MIC] Re-initialising microphone...")
                errors = 0
                time.sleep(2)
            continue
        try:
            transcript = recognizer.recognize_google(audio, language=config.GOOGLE_LANG)
        except sr.UnknownValueError:
            continue
        except sr.RequestError as e:
            print(f"[STT ERROR] {e}")
            continue
        except Exception as e:
            print(f"[STT] {type(e).__name__}: {e}")
            continue
        print(f"[HEARD] {transcript}")
        if wake_detected(transcript):
            print(f"[WAKE] {transcript}")
            boot()


def main():
    print("=" * 50)
    print(" J.A.R.V.I.S. wake-word launcher")
    print(" Pre-loading Ollama + web app, then listening...")
    print(" Say 'Jarvis' to open the web app.")
    print(" Ctrl+C to quit.")
    print("=" * 50)
    _init_tts()
    # Pre-boot everything in the background at login.
    t = threading.Thread(target=ensure_ollama, daemon=True)
    t.start()
    threading.Thread(target=ensure_webapp, daemon=True).start()
    time.sleep(1)
    listen_loop()


if __name__ == "__main__":
    main()