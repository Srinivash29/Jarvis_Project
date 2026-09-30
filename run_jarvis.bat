@echo off
title JARVIS AI Assistant
cd /d "%~dp0"

echo ========================================================
echo               STARTING JARVIS (MARK LI)                 
echo ========================================================
echo.

:: Detect virtual environment Python or fallback to system Python
if exist ".venv\Scripts\python.exe" (
    set "PY_EXE=.venv\Scripts\python.exe"
) else if exist "venv\Scripts\python.exe" (
    set "PY_EXE=venv\Scripts\python.exe"
) else (
    set "PY_EXE=python"
)

"%PY_EXE%" main.py

if %ERRORLEVEL% neq 0 (
    echo.
    echo ========================================================
    echo JARVIS exited with error code %ERRORLEVEL%.
    echo ========================================================
    pause
)
