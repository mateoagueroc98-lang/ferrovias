@echo off
rem Abre la app en la compu del trabajo (Windows): actualiza main, arranca la app y la abre en Chrome.
rem Hacer doble clic, o crear un acceso directo en el escritorio (clic derecho > Enviar a > Escritorio).
title Ferrovias - app
cd /d "%~dp0"
git checkout main
git pull
start "" cmd /c "timeout /t 10 >/dev/null & start chrome http://localhost:8501"
py -3.13 -m streamlit run app.py --server.headless true
pause
