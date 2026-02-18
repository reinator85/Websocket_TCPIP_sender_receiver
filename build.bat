@echo off
echo ========================================
echo    Compilar WebSocket Server (PyInstaller)
echo ========================================
echo.

echo Activando entorno virtual...
call venv\Scripts\activate.bat

echo.
echo Instalando PyInstaller si no esta instalado...
pip install -r requirements-build.txt

echo.
echo Compilando con PyInstaller...
pyinstaller websocket_server.spec

echo.
if exist "dist\WebSocketServer.exe" (
    echo ========================================
    echo    Compilacion exitosa.
    echo    Ejecutable: dist\WebSocketServer.exe
    echo ========================================
) else (
    echo Error: no se genero dist\WebSocketServer.exe
)

echo.
pause
