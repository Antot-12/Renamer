@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ============================================
echo    Збірка Renamer.exe (мінімальний розмір)
echo ============================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo ❌ Спочатку запустіть install.bat
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat
pip show pyinstaller >nul 2>&1 || pip install pyinstaller -q

:: Download UPX compressor (reduces size by 50-60%%)
if not exist "upx\upx.exe" (
    echo Завантаження UPX компресора...
    curl -L -o upx.zip https://github.com/upx/upx/releases/download/v4.2.4/upx-4.2.4-win64.zip 2>nul
    if exist upx.zip (
        powershell -command "Expand-Archive -Path upx.zip -DestinationPath . -Force" 2>nul
        if exist upx-4.2.4-win64 (
            ren upx-4.2.4-win64 upx
        )
        del upx.zip 2>nul
    )
)

echo Збірка з оптимізацією...
echo.

if exist "upx\upx.exe" (
    pyinstaller --noconfirm --upx-dir=upx Renamer.spec
) else (
    pyinstaller --noconfirm Renamer.spec
)

if errorlevel 1 (
    echo ❌ Помилка! / Error!
    pause
    exit /b 1
)

echo.
echo ============================================
echo ✅ Готово! dist\Renamer.exe
for %%A in (dist\Renamer.exe) do (
    set /a SIZE_MB=%%~zA / 1048576
    echo    Розмір: %%~zA bytes
)
echo ============================================
pause
