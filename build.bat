@echo off
echo ========================================
echo    Build Sender/Receiver V1.0 (PyInstaller)
echo ========================================
echo.

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo.
echo Installing dependencies and PyInstaller...
pip install -r requirements.txt
pip install -r requirements-build.txt

echo.
echo Building with PyInstaller...
pyinstaller websocket_server.spec

echo.
if exist "dist\SenderReceiver-V1.0.exe" (
    echo ========================================
    echo    Build successful. (V1.0)
    echo    Executable: dist\SenderReceiver-V1.0.exe
    echo ========================================
) else (
    echo Error: dist\SenderReceiver-V1.0.exe was not generated
)

echo.
pause
