@echo off
echo ========================================
echo    Build Sender/Receiver V1.1 (PyInstaller)
echo ========================================
echo.

if not exist "venv\Scripts\python.exe" (
    echo ERROR: venv no encontrado. Ejecuta setup_env.bat primero.
    pause
    exit /b 1
)

echo.
echo Installing dependencies and PyInstaller...
venv\Scripts\python.exe -m pip install -r requirements.txt
venv\Scripts\python.exe -m pip install -r requirements-build.txt

echo.
echo Building with PyInstaller...
venv\Scripts\python.exe -m PyInstaller websocket_server.spec

echo.
if exist "dist\SenderReceiver-V1.1.exe" (
    echo ========================================
    echo    Build successful. ^(V1.1^)
    echo    Executable: dist\SenderReceiver-V1.1.exe
    echo ========================================
) else (
    echo Error: dist\SenderReceiver-V1.1.exe was not generated
)

echo.
pause
