@echo off
title Build Dota Ready Helper

echo ========================================
echo   Build Dota Ready Helper
echo ========================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found!
    pause
    exit /b 1
)

echo [1/2] Building .exe...
echo.

REM Build GUI version with icon and system tray
pyinstaller --clean --onefile --windowed --name "DotaReadyHelper" --icon "assets/icon.ico" --add-data "assets;assets" --add-data ".env.example;." main_gui.py

if errorlevel 1 (
    echo.
    echo ERROR: Build failed!
    pause
    exit /b 1
)

echo.
echo SUCCESS: Build completed!
echo.
echo File: dist\DotaReadyHelper.exe
echo.

REM Show size
for %%A in ("dist\DotaReadyHelper.exe") do echo Size: %%~zA bytes

echo.
echo Run the program? (Y/N)
set /p choice=
if /i "%choice%"=="Y" (
    cd dist
    start "" "DotaReadyHelper.exe"
    cd ..
)

echo.
pause
