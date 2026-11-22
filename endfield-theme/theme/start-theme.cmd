@echo off
rem ZCode Endfield Industrial Theme launcher
cd /d "%~dp0"
start "" http://127.0.0.1:8642/
where python >nul 2>nul
if %errorlevel%==0 (
  python stats_server.py
) else (
  py -3 stats_server.py
)
