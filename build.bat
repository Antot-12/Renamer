@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ============================================
echo    Renamer - Build Portable EXE
echo ============================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.9+ from https://python.org
    pause
    exit /b 1
)

REM Check if venv exists, create if not
if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
)

REM Activate venv
call .venv\Scripts\activate.bat

REM Install/upgrade dependencies
echo.
echo Installing dependencies...
pip install --upgrade pip >nul 2>&1
pip install -r requirements.txt >nul 2>&1
pip install pyinstaller >nul 2>&1

REM Clean previous builds
echo.
echo Cleaning previous builds...
if exist "dist" rmdir /s /q dist
if exist "build" rmdir /s /q build
if exist "Renamer.spec" del /q Renamer.spec

REM Download UPX compressor for smaller size
if not exist "upx\upx.exe" (
    echo.
    echo Downloading UPX compressor for smaller EXE size...
    curl -L -o upx.zip https://github.com/upx/upx/releases/download/v4.2.4/upx-4.2.4-win64.zip 2>nul
    if exist upx.zip (
        powershell -command "Expand-Archive -Path upx.zip -DestinationPath . -Force" 2>nul
        if exist upx-4.2.4-win64 (
            ren upx-4.2.4-win64 upx
        )
        del upx.zip 2>nul
        echo UPX downloaded successfully.
    ) else (
        echo Could not download UPX. Building without compression.
    )
)

REM Build with PyInstaller (optimized for small size)
echo.
echo Building portable EXE (this may take a few minutes)...
echo.

REM Set UPX option if available
set UPX_OPT=
if exist "upx\upx.exe" (
    set UPX_OPT=--upx-dir=upx
    echo Using UPX compression...
) else (
    set UPX_OPT=--noupx
)

pyinstaller ^
    --onefile ^
    --windowed ^
    --name=Renamer ^
    --icon=ico.ico ^
    --add-data "ico.ico;." ^
    %UPX_OPT% ^
    --strip ^
    --exclude-module numpy ^
    --exclude-module scipy ^
    --exclude-module pandas ^
    --exclude-module matplotlib ^
    --exclude-module pytest ^
    --exclude-module _pytest ^
    --exclude-module setuptools ^
    --exclude-module wheel ^
    --exclude-module pip ^
    --exclude-module doctest ^
    --exclude-module pdb ^
    --exclude-module unittest ^
    --exclude-module lib2to3 ^
    --exclude-module xmlrpc ^
    --exclude-module pydoc ^
    --exclude-module test ^
    --exclude-module tkinter.test ^
    --exclude-module email.test ^
    --exclude-module idlelib ^
    --exclude-module sqlite3 ^
    --exclude-module multiprocessing ^
    --exclude-module asyncio ^
    --exclude-module concurrent ^
    --exclude-module curses ^
    --exclude-module ftplib ^
    --exclude-module http.server ^
    --exclude-module socketserver ^
    --clean ^
    run.py

REM Check if build succeeded
if exist "dist\Renamer.exe" (
    echo.
    echo ============================================
    echo    BUILD SUCCESSFUL!
    echo ============================================
    echo.

    REM Show file size
    for %%A in ("dist\Renamer.exe") do (
        set /a SIZE_MB=%%~zA / 1048576
        echo Output: dist\Renamer.exe
        echo Size: approximately !SIZE_MB! MB ^(%%~zA bytes^)
    )

    setlocal enabledelayedexpansion
    for %%A in ("dist\Renamer.exe") do (
        set /a SIZE_MB=%%~zA / 1048576
        echo.
        echo File: dist\Renamer.exe
        echo Size: !SIZE_MB! MB ^(%%~zA bytes^)
    )
    endlocal

    echo.
    echo You can now copy Renamer.exe anywhere and run it!
    echo No Python installation required.
    echo.
) else (
    echo.
    echo ============================================
    echo    BUILD FAILED
    echo ============================================
    echo.
    echo Check the error messages above.
    echo.
)

REM Cleanup build artifacts (keep dist)
echo Cleaning up build artifacts...
if exist "build" rmdir /s /q build
if exist "Renamer.spec" del /q Renamer.spec

echo.
pause
