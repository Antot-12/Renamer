@echo off
chcp 65001 >nul
cd /d "%~dp0"

:: Check if venv exists
if not exist ".venv\Scripts\python.exe" (
    echo ❌ Віртуальне середовище не знайдено / Virtual environment not found
    echo    Спочатку запустіть / First run:
    echo    install.bat
    pause
    exit /b 1
)

:: Run with venv Python
.venv\Scripts\python.exe run.py

if errorlevel 1 (
    echo.
    echo ❌ Помилка запуску / Launch error
    pause
)
