# J.A.R.V.I.S. — Local AI Assistant

A voice + chat AI assistant in the style of Iron Man's J.A.R.V.I.S. Runs on **Ollama** locally (optional Gemini cloud fallback). Includes a full desktop voice assistant and a browser web app.

**Developed by A. Kritthik Shriraman**

---

## What you need first

| Requirement | Windows | macOS / Linux |
|---|---|---|
| **Python 3.10+** | python.org or Microsoft Store | python.org / apt / brew |
| **Ollama** | [ollama.com](https://ollama.com) (installer) | `curl -fsSL https://ollama.com/install.sh \| sh` |
| **A microphone** | built-in is fine | built-in is fine |

Then pull the local model (the one this project uses by default):

```bash
ollama pull qwen2.5:3b
```

> Not a Windows/macOS/Linux user is locked to those — covered above. Everything works on plain Python with no Docker needed.

---

## 1. Get the code

```bash
git clone https://github.com/kshriraman209-coder/jarvis-assistant.git
cd jarvis-assistant
```

(Or download the ZIP from the repo page and unzip it.)

---

## 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

If `requirements.txt` is missing, install manually:

```bash
pip install flask pyttsx3 pyaudio speechrecognition requests
```

**Windows note:** if `pyaudio` fails to install, run:

```bash
pip install pipwin
pipwin install pyaudio
```

---

## 3. Make sure Ollama is running

```bash
ollama serve
```

Keep that terminal open. (On Windows the Ollama app usually starts automatically.)

---

## 4. Run the WEB APP (recommended way to try it)

```bash
python webapp.py
```

Then open **http://127.0.0.1:5000** in your browser. You'll get an Iron-Man-style chat interface: click the microphone to talk, type commands, or press the quick-action buttons (open apps, search Google/YouTube, take screenshots, etc.).

---

## 5. Run the VOICE ASSISTANT (Jarvis, desktop style)

```bash
python main.py
```

Then speak:

- **"Jarvis"** — wake word to activate
- **"What time is it?"**, **"Open Chrome"**, **"Search for cats"**, etc.
- **"goodbye"** — quit

It needs a microphone and speakers for full hands-free use.

---

## Model options

| Mode | Model | Requires |
|---|---|---|
| **ollama** (default) | `qwen2.5:3b` — fully local, private | Ollama running |
| **gemini** | `gemini-2.0-flash` (cloud) | Your own Gemini API key |

To switch modes, edit `config.py` line 13:

```python
PROVIDER = "ollama"   # or "gemini"
```

If you use Gemini, set your key before running (never commit it):

```powershell
# Windows PowerShell
$env:GEMINI_API_KEY = "your-key-here"
```

```bash
# macOS / Linux
export GEMINI_API_KEY="your-key-here"
```

The web app also has a **dropdown in the top bar** to switch between the two models live, without editing files.

---

## Example commands

| Type | Say / type |
|---|---|
| System | "What time is it?" · "Date" · "System status" |
| Apps | "Open Chrome" · "Open Notepad" · "Open Spotify" |
| Web | "Open YouTube" · "Open Google" · "Open GitHub" |
| Search | "Search Google for python tutorials" · "Search YouTube for lofi" |
| Screen | "Take a screenshot" · "Lock the screen" |
| Mouse/keys | "Move the mouse to 960, 500" · "Type hello" · "Scroll down" |
| Fun chat | "Tell me a fun fact" · "Explain how a jet engine works" |

---

## Troubleshooting

- **"No microphone found"** → plug one in, or check mic permissions in your OS.
- **"Ollama not reachable"** → run `ollama serve`, then re-try.
- **Model not found** → run `ollama pull qwen2.5:3b`.
- **TTS/voice silent** → your Windows has no SAPI voice; replies still show on screen.
- **Browser mic not working** → use Chrome or Edge (Firefox often blocks the web mic).
- **Port 5000 in use** → change the port at the bottom of `webapp.py`.

---

© 2026 A. Kritthik Shriraman