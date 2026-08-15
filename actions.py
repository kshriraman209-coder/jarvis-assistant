import ctypes
import datetime
import os
import shutil
import subprocess
import sys
import threading
import time
from ctypes import wintypes
import webbrowser

import psutil
import pyautogui

import config

APP_ALIASES = {
    "notepad": "notepad",
    "notepad++": "notepad++",
    "calculator": "calc",
    "calc": "calc",
    "paint": "mspaint",
    "snip": "snippingtool",
    "snipping tool": "snippingtool",
    "cmd": "cmd",
    "command prompt": "cmd",
    "terminal": "wt",
    "powershell": "powershell",
    "explorer": "explorer",
    "file explorer": "explorer",
    "files": "explorer",
    "control panel": "control",
    "task manager": "taskmgr",
    "settings": "ms-settings:",
    "settings:": "ms-settings:",
    "this pc": "explorer",
    "word": "winword",
    "excel": "excel",
    "powerpoint": "powerpoint",
    "chrome": "chrome",
    "google chrome": "chrome",
    "edge": "msedge",
    "firefox": "firefox",
    "spotify": "spotify",
    "vs code": "code",
    "visual studio code": "code",
    "code": "code",
    "paint": "mspaint",
    "whatsapp": "whatsapp",
    "telegram": "telegram",
    "discord": "discord",
    "zoom": "zoom",
    "teams": "teams",
    "slack": "slack",
    "vlc": "vlc",
    "media player": "wmplayer",
    "photoshop": "photoshop",
    "blender": "blender",
    "obs": "obs64",
    "steam": "steam",
    "epic games": "epicgameslauncher",
    "visual studio": "devenv",
}

APP_EXECUTABLES = {
    "notepad++": ["notepad++", "notepad++64"],
    "chrome": ["chrome", "msedge"],
    "spotify": ["spotify"],
    "vs code": ["code", "Code"],
    "code": ["code", "Code"],
    "winword": ["WINWORD", "winword"],
    "excel": ["EXCEL", "excel"],
    "powerpoint": ["POWERPNT", "powerpoint"],
    "firefox": ["firefox"],
}


def _find_executable(name):
    exes_to_try = APP_EXECUTABLES.get(name, [name])
    for exe in exes_to_try:
        found = shutil.which(exe)
        if found:
            return found
        for base in [r"C:\Program Files", r"C:\Program Files (x86)"]:
            if not os.path.isdir(base):
                continue
            for root, dirs, files in os.walk(base):
                dirs[:] = [d for d in dirs
                           if d not in ("Windows", "node_modules", "WindowsApps", "$RECYCLE.BIN",
                                        "Common Files", "Microsoft Shared")]
                if root[len(base):].count(os.sep) >= 3:
                    dirs[:] = []
                if exe.lower() + ".exe" in (f.lower() for f in files):
                    return os.path.join(root, exe + ".exe")
    return None


_store_apps = None


def _find_store_app(name):
    """Look up a Windows Store app by display name via shell:AppsFolder."""
    global _store_apps
    key = name.lower()
    if _store_apps is None:
        _store_apps = {}
        script = (
            "$shell = New-Object -ComObject Shell.Application; "
            "foreach ($a in $shell.Namespace('shell:AppsFolder').Items()) "
            "{ Write-Output ($a.Name + '|' + $a.Path) }"
        )
        try:
            raw = subprocess.run(
                ["powershell", "-NoProfile", "-Command", script],
                capture_output=True, text=True, timeout=30,
            ).stdout
        except Exception:
            return None
        for line in raw.splitlines():
            if "|" in line:
                nm, path = line.split("|", 1)
                _store_apps[nm.lower()] = path
    for nm in sorted(_store_apps):
        if key in nm:
            return _store_apps[nm]
    return None


def _launch(exe):
    """Launch an exe, falling back to startfile for restricted/elevated targets."""
    if "WindowsApps" in exe:
        return False
    try:
        subprocess.Popen([exe], shell=False)
        return True
    except Exception:
        pass
    try:
        os.startfile(exe)
        return True
    except Exception:
        return False


def _find_start_menu(name):
    """Find a Start Menu shortcut (.lnk) whose filename matches name."""
    key = name.lower().replace(" ", "")
    start_dirs = [
        os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs"),
        r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs",
    ]
    for base in start_dirs:
        if not os.path.isdir(base):
            continue
        for root, dirs, files in os.walk(base):
            dirs[:] = [d for d in dirs if d not in ("node_modules",)]
            try:
                for f in files:
                    fl = f.lower()
                    if fl.endswith(".lnk"):
                        clean = fl[:-4].replace(" ", "")
                        if key in clean or key in fl:
                            return os.path.join(root, f)
            except Exception:
                continue
    return None


def _snapshot_pids():
    """Return the set of currently running process PIDs."""
    try:
        return {p.pid for p in psutil.process_iter(["pid"])}
    except Exception:
        return set()


def _activate_windows(pids, key=None):
    """Fully show & focus the window of a newly launched app.

    Works around Windows' foreground-lock with two standard techniques:
      1. Simulated ALT-key press (the classic trick automation tools use) so a
         background process is allowed to call SetForegroundWindow.
      2. Matching windows by process name so Store/UWP apps (whose real window
         PID differs from the launcher) get picked up too.
    """
    if sys.platform != "win32":
        return
    try:
        user32 = ctypes.windll.user32
        SW_SHOWNORMAL = 1
        key = (key or "").lower().replace(" ", "")

        def _collect():
            found = []

            @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
            def _cb(hwnd, lparam):
                if not user32.IsWindowVisible(hwnd):
                    return True
                wnd_pid = wintypes.DWORD()
                user32.GetWindowThreadProcessId(hwnd, ctypes.byref(wnd_pid))
                pid = wnd_pid.value
                if pid in pids:
                    found.append(hwnd)
                    return True
                if key:
                    try:
                        pname = psutil.Process(pid).name().lower().replace(" ", "")
                        if key in pname:
                            found.append(hwnd)
                    except Exception:
                        pass
                return True

            user32.EnumWindows(_cb, 0)
            return found

        # The window may take a moment to appear; poll for up to ~8s.
        for _ in range(26):
            found = _collect()
            if found:
                _force_foreground(found[0])
                return
            time.sleep(0.3)
    except Exception:
        pass


def _force_foreground(hwnd):
    """Show + activate a window even from a background process."""
    try:
        user32 = ctypes.windll.user32
        SW_SHOWNORMAL = 1
        VK_MENU = 0x12
        KEYEVENTF_KEYUP = 0x0002

        user32.ShowWindow(hwnd, SW_SHOWNORMAL)
        user32.BringWindowToTop(hwnd)
        # Simulated Alt press unlocks SetForegroundWindow for our process.
        user32.keybd_event(VK_MENU, 0, 0, 0)
        user32.keybd_event(VK_MENU, 0, KEYEVENTF_KEYUP, 0)
        user32.SetForegroundWindow(hwnd)
        user32.BringWindowToTop(hwnd)
    except Exception:
        pass


def open_app(name):
    app = next((k for k in APP_ALIASES if k in name), None)
    if not app:
        app = name.strip()
    target = APP_ALIASES.get(app, app)
    before = _snapshot_pids()
    # Store apps first (most reliable for modern apps like WhatsApp, Teams, etc.)
    if not target.startswith("ms-"):
        store = _find_store_app(app)
        if store:
            try:
                os.startfile(f"shell:AppsFolder\\{store}")
                _activate_windows(_snapshot_pids() - before, key=app)
                return True
            except Exception:
                pass
    # Next, Start Menu shortcut.
    lnk = _find_start_menu(app)
    if lnk:
        try:
            os.startfile(lnk)
            _activate_windows(_snapshot_pids() - before, key=app)
            return True
        except Exception:
            pass
    if target.startswith("ms-"):
        os.startfile(target)
        _activate_windows(_snapshot_pids() - before, key=app)
        return True
    exe = _find_executable(target)
    if exe:
        _launch(exe)
        _activate_windows(_snapshot_pids() - before, key=app)
        return True
    # Fall back: scan installed programs for a fuzzy name match.
    exe = _find_any_app(app)
    if exe:
        _launch(exe)
        _activate_windows(_snapshot_pids() - before, key=app)
        return True
    try:
        os.startfile(target)
        _activate_windows(_snapshot_pids() - before, key=app)
        return True
    except Exception:
        return False


def _find_any_app(name):
    """Search common install locations for an app whose filename matches name."""
    key = name.lower().replace(" ", "")
    want = key.replace(".exe", "")
    exes = []
    # Root-agnostic, budgeted scan.
    for base in [r"C:\Program Files", r"C:\Program Files (x86)",
                 os.path.expandvars(r"%LOCALAPPDATA%\Programs"), "C:\\Users"]:
        if not os.path.isdir(base):
            continue
        # Scan to depth 3 only, prune heavy dirs, skip WindowsApps entirely.
        for root, dirs, files in os.walk(base):
            depth = root[len(base):].count(os.sep)
            dirs[:] = [d for d in dirs
                       if d not in ("node_modules", "AppData",
                                    "$RECYCLE.BIN", "System Volume Information", "Common Files",
                                    "Microsoft Shared", "Temp", "cache", "WpSystem")]
            if depth >= 3:
                dirs[:] = []
            try:
                for f in files:
                    fl = f.lower()
                    if fl.endswith(".exe"):
                        base_name = fl[:-4].replace(" ", "")
                        if want in base_name or want in fl:
                            exes.append(os.path.join(root, f))
            except Exception:
                continue
            if len(exes) >= 5:
                break
        if len(exes) >= 5:
            break
    # Prefer non-Store apps; Store (WindowsApps) entries are a last resort.
    exes.sort(key=lambda p: ("WindowsApps" in p, p))
    for exe in exes:
        b = os.path.basename(exe).lower().replace(" ", "")
        if want in b:
            return exe
    return exes[0] if exes else None


def open_website(url):
    url = url if url.startswith("http") else f"https://{url}"
    os.startfile(url)
    return True


def open_folder(path):
    if os.path.isdir(path):
        os.startfile(path)
        return True
    return False


def get_time():
    now = datetime.datetime.now()
    return f"It is {now.strftime('%I:%M %p')}, sir." .replace(" 0", " ")


def get_date():
    now = datetime.datetime.now()
    return now.strftime("Today is %A, %B %d, %Y.")


def get_status():
    cpu = psutil.cpu_percent(interval=0.5)
    mem = psutil.virtual_memory()
    battery = psutil.sensors_battery()
    bat = f"Battery level at {int(battery.percent)} percent." if battery else "Battery info unavailable."
    return (
        f"CPU usage is {cpu} percent. "
        f"Memory usage is {mem.percent} percent, {mem.used//(1024**3)} of "
        f"{mem.total//(1024**3)} gigabytes in use. {bat}"
    )


def take_screenshot():
    folder = os.path.join(os.path.expanduser("~"), "JARVIS_Screenshots")
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, f"capture_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
    img = pyautogui.screenshot()
    img.save(path)
    return f"Screenshot saved to {path}"


def shutdown(delay=30):
    def _run():
        subprocess.run(["shutdown", "/s", "/t", str(delay)])
    threading.Thread(target=_run, daemon=True).start()
    return f"Shutting down in {delay} seconds." if delay else "Shutting down now."


def restart(delay=30):
    def _run():
        subprocess.run(["shutdown", "/r", "/t", str(delay)])
    threading.Thread(target=_run, daemon=True).start()
    return "Restarting in a few moments."


def cancel_shutdown():
    subprocess.run(["shutdown", "/a"])
    return "Shutdown cancelled."


def lock_screen():
    subprocess.run(["rundll32.exe", "user32.dll,LockWorkStation"])
    return "Locking the system."


def log_off():
    subprocess.run(["shutdown", "/l"])
    return "Logging you off."


def volume_up(step=4):
    pyautogui.press("volumeup", presses=step)
    return "Volume increased."


def volume_down(step=4):
    pyautogui.press("volumedown", presses=step)
    return "Volume decreased."


def mute():
    pyautogui.press("volumemute")
    return "Muted."


def key_sequence(keys):
    for k in keys:
        pyautogui.press(k)
    return "Done."


# ---------- Mouse & keyboard control (pyautogui) ----------

def move_mouse(x=0, y=0):
    """Move the cursor to absolute coordinates (0-1919, 0-1079)."""
    try:
        pyautogui.FAILSAFE = True
        screen_w, screen_h = pyautogui.size()
        cx = min(max(int(x), 0), screen_w - 1)
        cy = min(max(int(y), 0), screen_h - 1)
        pyautogui.moveTo(cx, cy, duration=0.25)
        return f"Pointer moved to {cx}, {cy}."
    except Exception as e:
        return f"Could not move pointer: {e}"


def click_mouse(button="left", count=1):
    """Click at the current cursor position. button: left|right|middle."""
    try:
        btn = {"left": "left", "right": "right", "middle": "middle"}.get(button, "left")
        for _ in range(int(count)):
            pyautogui.click(button=btn)
        return f"Clicked {button}, {count} time(s)."
    except Exception as e:
        return f"Could not click: {e}"


def scroll_mouse(direction="down", amount=3):
    """Scroll. direction: up|down. amount: number of notches."""
    try:
        amt = int(amount)
        pyautogui.scroll(-amt if direction == "down" else amt)
        return f"Scrolled {direction} by {amt}."
    except Exception as e:
        return f"Could not scroll: {e}"


def drag_mouse(x, y):
    """Drag from current position to absolute (x, y)."""
    try:
        pyautogui.dragTo(int(x), int(y), duration=0.5)
        return f"Dragged to {x}, {y}."
    except Exception as e:
        return f"Could not drag: {e}"


def type_text(text, interval=0.02):
    """Type text as if from the keyboard, then press Enter."""
    try:
        pyautogui.write(text, interval=float(interval))
        return f'Typed "{text}".'
    except Exception as e:
        return f"Could not type: {e}"


def press_keys(keys, combo=False):
    """Press keys (comma separated). combo=True to hold them together (hotkey)."""
    try:
        parts = [k.strip() for k in keys.split(",") if k.strip()]
        if combo and len(parts) > 1:
            pyautogui.hotkey(*parts)
        else:
            for k in parts:
                pyautogui.press(k)
        return f"Pressed {keys}."
    except Exception as e:
        return f"Could not press keys: {e}"


# ---------- Smart search (web + local) ----------

def google_search(query):
    url = "https://www.google.com/search?q=" + "+".join(query.split())
    open_website(url)
    return f"Searching Google for {query}, sir."


def bing_search(query):
    url = "https://www.bing.com/search?q=" + "+".join(query.split())
    open_website(url)
    return f"Searching Bing for {query}, sir."


def youtube_search(query):
    url = "https://www.youtube.com/results?search_query=" + "+".join(query.split())
    open_website(url)
    return f"Searching YouTube for {query}, sir."


def wikipedia_search(query):
    url = "https://en.wikipedia.org/wiki/" + "_".join(query.split())
    open_website(url)
    return f"Searching Wikipedia for {query}, sir."


def image_search(query):
    url = "https://www.google.com/search?tbm=isch&q=" + "+".join(query.split())
    open_website(url)
    return f"Searching images for {query}, sir."


# ---------- Smart local file/folder lookup ----------

def _candidate_roots():
    roots = [os.path.expanduser("~"), "C:\\"]
    if os.path.exists("D:\\"):
        roots.append("D:\\")
    return roots


def open_local(needle, kind="anything"):
    """Find and open a file/folder by name in common locations."""
    needle_l = needle.lower()
    hits = []
    for root in _candidate_roots():
        if not os.path.isdir(root):
            continue
        for base, dirs, files in os.walk(root):
            dirs[:] = [d for d in dirs if d not in ("Windows", "node_modules", "AppData", "$RECYCLE.BIN", "System Volume Information")]
            try:
                for entry in dirs + files:
                    if needle_l in entry.lower():
                        hits.append(os.path.join(base, entry))
            except Exception:
                continue
            if len(hits) >= 20:
                break
        if len(hits) >= 20:
            break
    if not hits:
        return False

    if kind in ("folder", "directory"):
        hits = [h for h in hits if os.path.isdir(h)]
    if not hits:
        return False

    target = hits[0]
    if os.path.isdir(target):
        os.startfile(target)
        msg = f"Opened the folder {os.path.basename(target)}, sir."
    else:
        os.startfile(target)
        msg = f"Opened {os.path.basename(target)}, sir."
    return msg