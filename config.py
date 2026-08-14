import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

OLLAMA_HOST = "http://localhost:11434"
OLLAMA_MODEL = "qwen2.5:3b"
OLLAMA_STREAM = False
OLLAMA_CTX = 2048
OLLAMA_KEEP_ALIVE = "5m"

# Cloud brain (optional). Set PROVIDER="gemini" and put your key here.
# Get a free key at https://aistudio.google.com/apikey
PROVIDER = "gemini"            # "gemini" | "ollama"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-2.0-flash"
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "{model}:generateContent?key={key}"
)

WAKE_WORDS = ["jarvis", "jarvis?", "jar vy", "jarvis listen"]
ASSISTANT_NAME = "JARVIS"

MIC_DEVICE_INDEX = None
MIC_ENERGY_THRESHOLD = 300
MIC_PHRASE_TIME_LIMIT = 5
MIC_PAUSE_THRESHOLD = 0.8

GOOGLE_LANG = "en-US"

GREETING = "Good to see you, sir. All systems are online and ready."
SLEEP_REPLY = "Standing by, sir."
UNKNOWN_REPLY = "I'm sorry, I didn't catch that."
GOODBYE = "Signing off. Goodbye, sir."

TTS_RATE = 180
TTS_VOLUME = 1.0

script_dir = BASE_DIR