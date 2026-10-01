@echo off
rem Corre el bot una vez con config.yaml y deja la ventana abierta.
cd /d "%~dp0"
if not exist config.yaml (
  echo Falta config.yaml. Corre primero instalar.bat
  pause
  exit /b 1
)
venv\Scripts\python main.py config.yaml
echo.
pause
