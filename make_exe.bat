@echo off
title Build JARVIS.exe
cd /d "%~dp0"
echo Building JARVIS.exe (one-file, no-console)...
python -m PyInstaller --onefile --noconsole --name JARVIS --add-data "web/index.html;web" --exclude-module tensorflow --exclude-module keras --exclude-module torch --exclude-module matplotlib --exclude-module numpy --hidden-import pyttsx3.drivers --hidden-import pyttsx3.drivers.sapi5 --hidden-import edge_tts run_jarvis.py
echo.
echo Done. Your app is at: dist\JARVIS.exe
pause