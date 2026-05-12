@echo off
title Start Dota Ready Helper

echo ========================================
echo   Dota Ready Helper v2.1
echo ========================================
echo.

REM Check if .env exists
if not exist ".env" (
    echo ERROR: .env file not found!
    echo.
    echo Please create .env file with your Telegram tokens.
    echo You can copy .env.example and edit it.
    echo.
    pause
    exit /b 1
)

REM Run the program
python main.py

pause
