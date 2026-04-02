@echo off
setlocal
echo ========================================
echo    Crear entorno virtual (venv)
echo    Sender/Receiver - WebSocket ^& TCP/IP
echo ========================================
echo.

if exist "venv\Scripts\python.exe" (
    echo El entorno 'venv' ya existe.
    echo.
    set /p REINSTALL="Reinstalar dependencias? (S/N): "
    if /i "%REINSTALL%"=="S" goto install_deps
    echo Listo. Ejecuta run.bat para iniciar la aplicacion.
    pause
    exit /b 0
)

echo Creando entorno virtual en carpeta 'venv'...
python -m venv venv
if errorlevel 1 (
    echo ERROR: No se pudo crear el entorno. Comprueba que Python esta instalado y en el PATH.
    pause
    exit /b 1
)
echo Entorno creado correctamente.
echo.

:install_deps
if not exist "venv\Scripts\python.exe" (
    echo ERROR: No se encontro venv\Scripts\python.exe
    pause
    exit /b 1
)

echo Instalando dependencias en venv (requirements.txt)...
venv\Scripts\python.exe -m pip install --upgrade pip
venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR al instalar dependencias.
    pause
    exit /b 1
)
echo.
echo ========================================
echo    Listo.
echo    Ejecuta run.bat para iniciar la aplicacion.
echo ========================================
pause
