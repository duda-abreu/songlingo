@echo off
cd /d "%~dp0docs"
start "" /min cmd /c "python -m http.server 8765"
timeout /t 1 /nobreak >nul
start "" msedge --app=http://localhost:8765/defi-standalone.html --window-size=1300,850
