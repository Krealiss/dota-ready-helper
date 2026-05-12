@echo off
REM запуск системи
cd /d "%~dp0"
echo [AIVA] Запусаю систему...
python dota_ready_helper.py
pause
