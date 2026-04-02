@echo off
setlocal
echo ========================================
echo    Sender/Receiver - WebSocket ^& TCP/IP
echo ========================================
echo.

if not exist "venv\Scripts\python.exe" (
    echo ERROR: venv no encontrado. Ejecuta setup_env.bat primero.
    pause
    exit /b 1
)

echo.
echo Verifying dependencies...
venv\Scripts\python.exe -c "import paho.mqtt.client" >nul 2>&1
if errorlevel 1 (
    echo Missing dependency detected. Installing requirements...
    venv\Scripts\python.exe -m pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo ERROR: Could not install required dependencies.
        pause
        exit /b 1
    )
)

echo.
echo Running application (main.py)...
echo.

venv\Scripts\python.exe main.py

echo.
echo Application stopped.
pause 