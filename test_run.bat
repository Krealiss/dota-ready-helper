@echo off
title Test Dota Ready Helper

echo ========================================
echo   Test Dota Ready Helper
echo   (without building .exe)
echo ========================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found!
    pause
    exit /b 1
)

echo OK: Python found
echo.

REM Check dependencies
echo Checking dependencies...
python -c "import pyautogui, keyboard, telebot, PIL, dotenv" >nul 2>&1
if errorlevel 1 (
    echo WARNING: Some dependencies missing
    echo Installing...
    pip install -r requirements.txt
)

echo OK: Dependencies installed
echo.

REM Check .env
if not exist ".env" (
    echo WARNING: .env file not found!
    echo Creating from .env.example...
    copy .env.example .env
    echo.
    echo IMPORTANT: Edit .env and add your tokens!
    echo.
    notepad .env
    echo.
    echo Press Enter after editing...
    pause
)

echo OK: Configuration ready
echo.

echo Starting program (console version)...
echo.
echo To stop: press Ctrl+C or F7
echo.
python main.py

pause
