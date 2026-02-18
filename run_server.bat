@echo off
echo ========================================
echo    WebSocket Server
echo ========================================
echo.

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo.
echo Running WebSocket server...
echo.

python websocket_server.py

echo.
echo Server stopped.
pause 