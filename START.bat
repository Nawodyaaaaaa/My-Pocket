@echo off
title My Pocket - Finance Agent
cd /d "%~dp0"

echo Checking Ollama...
where ollama >nul 2>nul || (echo Ollama is not installed. Get it from https://ollama.com/download & pause & exit /b)
ollama list
echo.

echo Installing Python packages (first time only)...
python -m pip install -q -r requirements.txt

echo.
echo Starting My Pocket in your browser...
python -m streamlit run app.py
pause
