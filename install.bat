@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ============================================
echo    Перейменувач - Встановлення
echo    Renamer - Installation
echo ============================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python не знайдено! / Python not found!
    echo    Встановіть Python 3.9+ з / Install Python 3.9+ from:
    echo    https://www.python.org/downloads/
    echo.
    echo    ⚠️ При встановленні позначте "Add Python to PATH"
    pause
    exit /b 1
)

echo ✓ Python знайдено / Python found
python --version
echo.

:: Create venv if not exists
if not exist ".venv" (
    echo Створення віртуального середовища / Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo ❌ Не вдалося створити venv / Failed to create venv
        pause
        exit /b 1
    )
    echo ✓ Віртуальне середовище створено / Virtual environment created
)

:: Activate and install
echo.
echo Встановлення залежностей / Installing dependencies...
echo.

call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt

if errorlevel 1 (
    echo.
    echo ❌ Помилка встановлення! / Installation error!
    pause
    exit /b 1
)

echo.
echo ============================================
echo ✓ Встановлення завершено! / Installation complete!
echo ============================================
echo.
echo Тепер запустіть / Now run:
echo    run.bat
echo.
echo Або з командного рядка / Or from command line:
echo    .venv\Scripts\activate
echo    python run.py
echo ============================================
pause
