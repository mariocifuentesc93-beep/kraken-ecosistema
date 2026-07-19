@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] No se encontro el entorno virtual .venv.
    echo Consulte INSTALL_WINDOWS.md para crear e instalar el entorno.
    pause
    exit /b 1
)

call ".venv\Scripts\activate.bat"
python app.py
set "KRAKEN_EXIT_CODE=%ERRORLEVEL%"

if not "%KRAKEN_EXIT_CODE%"=="0" (
    echo.
    echo [ERROR] Kraken Bot termino con codigo %KRAKEN_EXIT_CODE%.
    pause
)

exit /b %KRAKEN_EXIT_CODE%
