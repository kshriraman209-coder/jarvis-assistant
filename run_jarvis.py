"""
run_jarvis.py — single-entry point for the compiled JARVIS.exe.

Starts the Flask web app, opens the browser, and keeps a wake-word listener
running so that saying "Jarvis" reopens the web app on demand.
All in ONE process (no subprocess juggling), which is ideal for PyInstaller.
"""

import os
import sys
import threading
import time
import webbrowser

import config
import webapp

WEB_URL = "http://127.0.0.1:5000"


def _run_server():
    from werkzeug.serving import make_server
    srv = make_server("127.0.0.1", 5000, webapp.app, threaded=True)
    srv.serve_forever()


def pre_boot():
    """Best-effort: make sure Ollama is up before the first chat."""
    try:
        import awaken
        awaken.ensure_ollama()
    except Exception:
        pass


def open_browser():
    for _ in range(20):
        try:
            import requests
            requests.get(WEB_URL + "/api/status", timeout=1)
            webbrowser.open(WEB_URL)
            return
        except Exception:
            time.sleep(0.4)


def wake_loop():
    try:
        import awaken
        awaken._init_tts()
        awaken.listen_loop()
    except Exception as e:
        print(f"[WAKE LOOP] {e}")
        time.sleep(5)


def main():
    print("=" * 50)
    print(" J.A.R.V.I.S.  -  tar pod zipped, sir.")
    print("=" * 50)
    # 1. Ollama quietly in the background.
    threading.Thread(target=pre_boot, daemon=True).start()
    # 2. Serve the web app in this process.
    server = threading.Thread(target=_run_server, daemon=True)
    server.start()
    # 3. Open the browser once the server is ready.
    threading.Thread(target=open_browser, daemon=True).start()
    # 4. Wake-word listener so "Jarvis" reopens the app.
    threading.Thread(target=wake_loop, daemon=True).start()
    # Keep the process alive.
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()