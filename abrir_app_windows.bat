@echo off
rem Abre la app (Windows): arranca la app y la abre en Chrome.
rem Hacer doble clic, o crear un acceso directo en el escritorio (clic derecho > Enviar a > Escritorio).
rem El proyecto vive en esta carpeta compartida (sin GitHub): no descarga nada.
title Ferrovias - app
cd /d "%~dp0"
start "" cmd /c "timeout /t 20 >NUL & start chrome http://localhost:8501"
py -3.13 -m streamlit run app.py --server.headless true
pause
