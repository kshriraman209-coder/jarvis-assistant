import re
import sys

import pyaudio
import pyttsx3
import requests
import speech_recognition as sr

import actions
import brain
import config


# ---------- Text to speech ----------

_tts = None


def init_tts():
    global _tts
    try:
        _tts = pyttsx3.init()
        _tts.setProperty("rate", config.TTS_RATE)
        _tts.setProperty("volume", config.TTS_VOLUME)
        return True
    except Exception as e:
        print(f"[WARN] TTS unavailable: {e}")
        return False


def speak(text):
    print(f"[JARVIS] {text}")
    if _tts:
        _tts.say(text)
        _tts.runAndWait()


# ---------- Speech recognition ----------

def check_mic():
    try:
        pa = pyaudio.PyAudio()
        count = pa.get_device_count()
        if count == 0:
            return False
        pa.terminate()
        return True
    except Exception:
        return False


def check_ollama():
    try:
        resp = requests.get(f"{config.OLLAMA_HOST}/api/tags", timeout=5)
        resp.raise_for_status()
        models = [m.get("name") for m in resp.json().get("models", [])]
        if not any(m.startswith(config.OLLAMA_MODEL.split(":")[0]) for m in models):
            print(f"[WARN] Model '{config.OLLAMA_MODEL}' not found. Pull it with: ollama pull {config.OLLAMA_MODEL}")
        return True
    except Exception as e:
        print(f"[ERROR] Ollama not reachable at {config.OLLAMA_HOST}: {e}")
        return False


# ---------- Wake word + command detection ----------

def wake_word_detected(transcript):
    low = transcript.lower()
    return any(w in low for w in config.WAKE_WORDS)


def strip_wake_word(transcript):
    low = transcript.lower()
    for w in sorted(config.WAKE_WORDS, key=len, reverse=True):
        if w in low:
            return re.sub(re.escape(w), "", low, count=1).strip(' ,.?!')
    return low


def listen(prompt=None, timeout=5, phrase_time=5):
    recognizer = sr.Recognizer()
    recognizer.energy_threshold = config.MIC_ENERGY_THRESHOLD
    recognizer.dynamic_energy_threshold = True
    recognizer.pause_threshold = config.MIC_PAUSE_THRESHOLD
    try:
        with sr.Microphone(device_index=config.MIC_DEVICE_INDEX) as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.6)
            if prompt:
                print(f"[LISTENING] {prompt}")
            else:
                print("[LISTENING] ...")
            audio = recognizer.listen(
                source, timeout=timeout, phrase_time_limit=phrase_time
            )
    except sr.WaitTimeoutError:
        return ""
    except Exception as e:
        print(f"[ERROR] Microphone problem: {e}")
        return ""

    try:
        return recognizer.recognize_google(audio, language=config.GOOGLE_LANG).strip()
    except sr.UnknownValueError:
        return ""
    except sr.RequestError as e:
        print(f"[ERROR] Speech service error: {e}")
        return ""


# ---------- Command handling ----------

AGENT_KEYS = [
    ("jarvis", "jarvis"),
    ("whatsapp", "whatsapp"),
]

APP_MATCHERS = [
    ("open notepad", "notepad"),
    ("open calculator", "calculator"),
    ("open paint", "paint"),
    ("open command prompt", "cmd"),
    ("open terminal", "terminal"),
    ("open powershell", "powershell"),
    ("open explorer", "explorer"),
    ("open file explorer", "explorer"),
    ("open control panel", "control panel"),
    ("open task manager", "task manager"),
    ("open settings", "settings"),
    ("open word", "word"),
    ("open excel", "excel"),
    ("open powerpoint", "powerpoint"),
    ("open chrome", "chrome"),
    ("open google chrome", "chrome"),
    ("open edge", "edge"),
    ("open firefox", "firefox"),
    ("open spotify", "spotify"),
    ("open whatsapp", "whatsapp"),
    ("open telegram", "telegram"),
    ("open discord", "discord"),
    ("open zoom", "zoom"),
    ("open teams", "teams"),
    ("open slack", "slack"),
    ("open vlc", "vlc"),
    ("open media player", "wmplayer"),
    ("open photoshop", "photoshop"),
    ("open blender", "blender"),
    ("open obs", "obs64"),
    ("open steam", "steam"),
    ("open epic games", "epicgameslauncher"),
    ("open vs code", "vs code"),
    ("open visual studio code", "vs code"),
    ("open visual studio", "devenv"),
    ("open notepad plus plus", "notepad++"),
    ("open plus plus", "notepad++"),
    ("open notepad plus", "notepad++"),
    ("open snipping tool", "snipping tool"),
    ("open snipping", "snipping tool"),
]

WEBSITE_MATCHERS = [
    ("open youtube", "https://www.youtube.com"),
    ("open google", "https://www.google.com"),
    ("open github", "https://www.github.com"),
    ("open gmail", "https://mail.google.com"),
    ("open yahoo", "https://www.yahoo.com"),
    ("open twitter", "https://www.twitter.com"),
    ("open x", "https://www.x.com"),
    ("open instagram", "https://www.instagram.com"),
    ("open facebook", "https://www.facebook.com"),
    ("open reddit", "https://www.reddit.com"),
    ("open linkedin", "https://www.linkedin.com"),
    ("open whatsapp web", "https://web.whatsapp.com"),
    ("open netflix", "https://www.netflix.com"),
    ("open amazon", "https://www.amazon.com"),
    ("open flipkart", "https://www.flipkart.com"),
    ("open wikipedia", "https://www.wikipedia.org"),
    ("open stack overflow", "https://stackoverflow.com"),
    ("open google meet", "https://meet.google.com"),
    ("open chat gpt", "https://chatgpt.com"),
    ("open translate", "https://translate.google.com"),
    ("open maps", "https://maps.google.com"),
    ("open google drive", "https://drive.google.com"),
    ("open google docs", "https://docs.google.com"),
    ("open outlook", "https://outlook.live.com"),
    ("open youtube and search for", "youtube_search"),
]


def _num(text):
    m = re.search(r"\d+", text)
    return int(m.group()) if m else None


def handle_command(text):
    low = text.lower()

    # ---- System info ----
    if re.search(r"\b(time|clock)\b", low):
        return actions.get_time()
    if re.search(r"\bdate\b", low) and not re.search(r"\bupdate\b", low):
        return actions.get_date()
    if re.search(r"system status|cpu|memory usage|battery|how.{0,5}(cpu|memory|ram)", low):
        return actions.get_status()

    # ---- Screen / system actions ----
    if "screenshot" in low:
        return actions.take_screenshot()
    if re.search(r"lock the (screen|computer|pc|system)|\b(lock|locks)\b.*screen", low):
        return actions.lock_screen()
    if re.search(r"log ?off|log out|sign out", low):
        return actions.log_off()
    if re.search(r"shut ?down", low):
        return actions.shutdown()
    if re.search(r"restart|reboot", low):
        return actions.restart()
    if re.search(r"cancel.*(shut ?down|restart)", low):
        return actions.cancel_shutdown()

    # ---- Audio ----
    if re.search(r"\b(mute|unmute|silence)\b", low):
        return actions.mute()
    if re.search(r"\bvolume (up|raise|increase|max)\b", low):
        return actions.volume_up()
    if re.search(r"\bvolume (down|lower|decrease|min)\b", low):
        return actions.volume_down()

    # ---- Mouse control ----
    m = re.search(r"(?:move|put|point) (?:the )?mouse (?:to|at) (\d{1,4}),\s*(\d{1,4})", low)
    if m:
        return actions.move_mouse(m.group(1), m.group(2))
    if re.search(r"\bclick\b.*right|right\s*click", low):
        return actions.click_mouse("right")
    if re.search(r"\bdouble\s*click", low):
        return actions.click_mouse("left", 2)
    if re.search(r"\bclick\b", low):
        return actions.click_mouse("left")
    m = re.search(r"(?:scroll|move scroll|slide) (up|down)", low)
    if m:
        amt = _num(low) or 3
        return actions.scroll_mouse(m.group(1), amt)
    m = re.search(r"(?:drag|drag the mouse) (?:to|from) (\d{1,4}),\s*(\d{1,4})", low)
    if m:
        return actions.drag_mouse(m.group(1), m.group(2))

    # ---- Keyboard control ----
    m = re.search(r"(?:type|write|enter)\s+(?:the text )?(.+)", low)
    if m and not re.search(r"type of|what type", low):
        return actions.type_text(m.group(1).strip())
    m = re.search(r"(?:press|hit)\s+key\s*:\s*([a-z0-9 ,]+)$", low)
    if m:
        return actions.press_keys(m.group(1))
    m = re.search(r"(?:press|hit)\s+(ctrl|control|alt|shift)\s*\+\s*([a-z0-9]+)", low)
    if m:
        return actions.press_keys(f"{m.group(1)},{m.group(2)}", combo=True)

    # ---- Search commands ----
    if "image" in low and re.search(r"search|find|google", low):
        q = re.sub(r".*(?:search|find|google)\s*(?:for\s*)?", "", low).replace(" images", "").strip()
        if q:
            return actions.image_search(q)
    if "youtube" in low and re.search(r"search|find|play", low):
        q = re.sub(r".*(?:search|find|play)\s*(?:for\s*)?", "", low).replace(" on youtube", "").strip()
        if q:
            return actions.youtube_search(q)
    if "wikipedia" in low and re.search(r"search|find|look up", low):
        q = re.sub(r".*(?:search|find|look up)\s*(?:for\s*)?", "", low).replace(" on wikipedia", "").strip()
        if q:
            return actions.wikipedia_search(q)
    if "bing" in low and re.search(r"search|find", low):
        q = re.sub(r".*(?:search|find)\s*(?:for\s*)?", "", low).replace(" on bing", "").strip()
        if q:
            return actions.bing_search(q)
    if re.search(r"\bsearch .+ for .+|google .+|\bsearch for .+\b|search the web for", low):
        q = re.sub(r".*(?:search|google)\s*(?:for\s*)?", "", low)
        q = re.sub(r"\s+(on|for|about)\s+(google|the web|internet)$", "", q).strip()
        if q:
            return actions.google_search(q)

    # ---- Open anything: apps ----
    for phrase, app in APP_MATCHERS:
        if phrase in low:
            if actions.open_app(app):
                return f"Opening {app}, sir."
            return f"I'm afraid I could not launch {app}, sir."

    # ---- Open websites ----
    for phrase, url in WEBSITE_MATCHERS:
        if phrase in low:
            actions.open_website(url)
            return f"Opening {url.replace('https://www.', '')} for you, sir."

    # ---- Open local files / folders by name ----
    m = re.search(r"(?:open|launch|show)\s+(?:the\s+)?(?:file\s+|folder\s+|document\s+)?(.+)$", low)
    if m:
        needle = m.group(1).strip()
        if needle and len(needle) > 2 and needle not in (
            "it", "that", "this", "them", "now", "please", "up", "down", "the",
        ):
            kind = "folder" if "folder" in low else "anything"
            result = actions.open_local(needle, kind)
            if result:
                return result

    # ---- Generic exit ----
    if re.search(r"\bi am (?:done|finished|leaving|going)|sign ?off|goodbye|bye\b", low):
        return None

    # ---- Fallback to LLM ----
    return brain.ask(text)


# ---------- Main loop ----------

def main():
    print("=" * 50)
    print(" J.A.R.V.I.S.  -  Local AI Assistant  (Ollama powered)")
    print("=" * 50)
    print(f" Brain model : {config.OLLAMA_MODEL}")
    print(f" Site        : {config.OLLAMA_HOST}")
    print(" Say  'Jarvis'  to activate me.")
    print(" Say  'goodbye'  to dismiss me.")
    print(" Ctrl+C to quit.\n")

    if not check_mic():
        print("[ERROR] No microphone found. Exiting.")
        sys.exit(1)
    if not check_ollama():
        print("[ERROR] Aborting.")
        sys.exit(1)
    init_tts()

    if _tts:
        speak(config.GREETING)

    try:
        while True:
            pos = listen(timeout=60, phrase_time=8)
            if not pos:
                continue
            print(f"[STT] {pos}")

            if wake_word_detected(pos):
                speak("Yes, sir?")
                command = listen(timeout=8, phrase_time=10)
                if not command:
                    speak(config.UNKNOWN_REPLY)
                    continue
                print(f"[STT] {command}")
                reply = handle_command(command)
                if reply is None:
                    speak(config.GOODBYE)
                    break
                speak(reply)
    except KeyboardInterrupt:
        print("\n[EXIT] Interrupted by user.")


if __name__ == "__main__":
    main()