@echo off
setlocal enableextensions
title J.A.R.V.I.S. Setup
echo.
echo  =====================================================
echo    J.A.R.V.I.S.  -  One-time setup wizard
echo  =====================================================
echo.

echo  [1/4] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
  echo   Python is NOT installed or not on PATH.
  echo   Install it from https://www.python.org/downloads/
  echo   IMPORTANT: tick "Add Python to PATH" during install, then run this again.
  pause
  exit /b 1
)
echo   Found: 
python --version

echo.
echo  [2/4] Checking Ollama...
where ollama >nul 2>&1
if errorlevel 1 (
  echo   Ollama is NOT installed.
  echo   Install it from https://ollama.com then run this file again.
  pause
  exit /b 1
)
echo   Found.

echo.
echo  [3/4] Installing Python packages (first run takes a few minutes)...
pip install -r requirements.txt
if errorlevel 1 (
  echo   Something failed installing packages. Check the internet and retry.
  pause
  exit /b 1
)
echo   Packages installed.

echo.
echo  [4/4] Downloading the AI brain model (qwen2.5:3b, ~2GB once)...
ollama pull qwen2.5:3b
if errorlevel 1 (
  echo   Model download failed. Run "ollama pull qwen2.5:3b" later to retry.
)

echo.
echo  =====================================================
echo   Setup complete!
echo
echo   To run the web app:   python webapp.py
echo   Then open http://127.0.0.1:5000 in your browser
echo   To run voice "Jarvis": python main.py
echo  =====================================================
echo.
pause
endlocal