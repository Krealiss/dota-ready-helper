@echo off
title Full Test - Dota Ready Helper

echo ========================================
echo   Full Test Suite
echo   Dota Ready Helper v2.1
echo ========================================
echo.

set PASSED=0
set FAILED=0

REM Test 1: Python
echo [1/8] Testing Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo FAIL: Python not found
    set /a FAILED+=1
) else (
    echo PASS: Python found
    set /a PASSED+=1
)

REM Test 2: Dependencies
echo [2/8] Testing dependencies...
python -c "import pyautogui, keyboard, telebot, PIL, dotenv" >nul 2>&1
if errorlevel 1 (
    echo FAIL: Some dependencies missing
    set /a FAILED+=1
) else (
    echo PASS: All dependencies installed
    set /a PASSED+=1
)

REM Test 3: Config
echo [3/8] Testing config...
python -c "from config import validate_config; exit(0 if validate_config() else 1)" >nul 2>&1
if errorlevel 1 (
    echo FAIL: Config validation failed
    set /a FAILED+=1
) else (
    echo PASS: Config valid
    set /a PASSED+=1
)

REM Test 4: Imports
echo [4/8] Testing imports...
python -c "from dota_helper import DotaHelper; from telegram_bot import TelegramBot; from stats_tracker import Statistics" >nul 2>&1
if errorlevel 1 (
    echo FAIL: Import error
    set /a FAILED+=1
) else (
    echo PASS: All imports work
    set /a PASSED+=1
)

REM Test 5: Assets
echo [5/8] Testing assets...
if not exist "assets\prinyat.png" (
    echo FAIL: Assets missing
    set /a FAILED+=1
) else (
    echo PASS: Assets found
    set /a PASSED+=1
)

REM Test 6: Stats module
echo [6/8] Testing stats module...
python -c "from stats_tracker import Statistics; s = Statistics(); print('OK')" >nul 2>&1
if errorlevel 1 (
    echo FAIL: Stats module error
    set /a FAILED+=1
) else (
    echo PASS: Stats module works
    set /a PASSED+=1
)

REM Test 7: Export module
echo [7/8] Testing export module...
python -c "from report_exporter import ReportExporter; from stats_tracker import Statistics; s = Statistics(); e = ReportExporter(s); print('OK')" >nul 2>&1
if errorlevel 1 (
    echo FAIL: Export module error
    set /a FAILED+=1
) else (
    echo PASS: Export module works
    set /a PASSED+=1
)

REM Test 8: Error handler
echo [8/8] Testing error handler...
python -c "from error_handler import CrashReporter, setup_exception_handler; print('OK')" >nul 2>&1
if errorlevel 1 (
    echo FAIL: Error handler error
    set /a FAILED+=1
) else (
    echo PASS: Error handler works
    set /a PASSED+=1
)

echo.
echo ========================================
echo   Test Results
echo ========================================
echo.
echo PASSED: %PASSED%/8
echo FAILED: %FAILED%/8
echo.

if %FAILED% EQU 0 (
    echo SUCCESS: All tests passed!
    echo.
    echo Ready to build and launch!
) else (
    echo WARNING: Some tests failed
    echo Please fix errors before building
)

echo.
pause
