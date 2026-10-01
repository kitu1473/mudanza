@echo off
rem Instala el bot (una sola vez). Requiere Python con el lanzador "py".
cd /d "%~dp0"
py -m venv venv || goto :error
venv\Scripts\python -m pip install --upgrade pip
venv\Scripts\python -m pip install -r requirements.txt || goto :error
if not exist config.yaml copy config.example.yaml config.yaml
echo.
echo Listo. Ahora abri config.yaml y completa bot_token y chat_room.
pause
exit /b 0
:error
echo Fallo la instalacion. Copia el error y pasaselo a Claude.
pause
exit /b 1
