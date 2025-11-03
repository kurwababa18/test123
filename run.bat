@echo off
cd /d "%~dp0"

echo ========================================
echo   POLYMARKET TERMINAL
echo ========================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found in PATH
    echo Please install Python 3.10 or higher from python.org
    pause
    exit /b 1
)

REM Create venv if missing
if not exist venv (
    echo [SETUP] Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment
        pause
        exit /b 1
    )
    echo [SETUP] Installing dependencies...
    call venv\Scripts\activate
    pip install --upgrade pip
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Failed to install dependencies
        pause
        exit /b 1
    )
    echo [SETUP] Setup complete!
    echo.
) else (
    call venv\Scripts\activate
)

REM Run the app
python app.py

if errorlevel 1 (
    echo.
    echo [ERROR] Application exited with error
    pause
    exit /b 1
)

pause
