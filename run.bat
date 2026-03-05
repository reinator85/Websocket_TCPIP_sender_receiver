@echo off
echo ========================================
echo    Sender/Receiver - WebSocket ^& TCP/IP
echo ========================================
echo.

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo.
echo Running application (main.py)...
echo.

python main.py

echo.
echo Application stopped.
pause 