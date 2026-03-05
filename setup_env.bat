@echo off
echo ========================================
echo    Crear entorno virtual (venv)
echo    Sender/Receiver - WebSocket ^& TCP/IP
echo ========================================
echo.

if exist "venv\Scripts\activate.bat" (
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
echo Activando entorno e instalando dependencias (requirements.txt)...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
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
