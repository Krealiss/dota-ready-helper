@echo off
setlocal enabledelayedexpansion
title Build Dota Ready Helper Installer

echo ========================================
echo   Dota Ready Helper - Build Installer
echo ========================================
echo.

REM Перевірка Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python не знайдено!
    pause
    exit /b 1
)

REM Перевірка PyInstaller
python -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
    echo ❌ PyInstaller не встановлено!
    echo Встановлюю...
    pip install pyinstaller
)

REM Перевірка Inno Setup
set INNO_PATH=C:\Program Files (x86)\Inno Setup 6\ISCC.exe
if not exist "%INNO_PATH%" (
    echo ❌ Inno Setup не знайдено!
    echo Завантаж з: https://jrsoftware.org/isdl.php
    pause
    exit /b 1
)

echo.
echo [1/4] Очищення старих файлів...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "installer" rmdir /s /q "installer"
echo ✅ Очищено

echo.
echo [2/4] Збірка .exe (GUI версія)...
pyinstaller --clean --onedir --windowed ^
    --name "DotaReadyHelper" ^
    --add-data "assets;assets" ^
    --hidden-import "PIL._tkinter_finder" ^
    main_gui.py

if errorlevel 1 (
    echo ❌ Помилка збірки .exe
    pause
    exit /b 1
)
echo ✅ .exe зібрано

echo.
echo [3/4] Компіляція інсталятора...
"%INNO_PATH%" installer.iss

if errorlevel 1 (
    echo ❌ Помилка компіляції інсталятора
    pause
    exit /b 1
)
echo ✅ Інсталятор зібрано

echo.
echo [4/4] Перевірка результату...
if exist "installer\DotaReadyHelper_Setup_v2.1.exe" (
    echo ✅ Інсталятор готовий!
    echo.
    echo 📦 Файл: installer\DotaReadyHelper_Setup_v2.1.exe

    REM Показати розмір
    for %%A in ("installer\DotaReadyHelper_Setup_v2.1.exe") do (
        set size=%%~zA
        set /a sizeMB=!size! / 1048576
        echo 📊 Розмір: !sizeMB! MB
    )

    echo.
    echo Хочеш запустити інсталятор для тестування? (Y/N)
    set /p choice=
    if /i "%choice%"=="Y" (
        start "" "installer\DotaReadyHelper_Setup_v2.1.exe"
    )
) else (
    echo ❌ Інсталятор не знайдено!
    pause
    exit /b 1
)

echo.
echo ========================================
echo   Збірка завершена успішно!
echo ========================================
pause
