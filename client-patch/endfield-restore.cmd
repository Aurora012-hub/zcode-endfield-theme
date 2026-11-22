@echo off
chcp 65001 >nul
cd /d "%~dp0"
title ZCode Endfield Skin - Restore
echo ============================================
echo   ZCODE ENDFIELD INDUSTRIAL SKIN - RESTORE
echo ============================================
echo.
:waitquit
tasklist /FI "IMAGENAME eq ZCode.exe" 2>nul | find /I "ZCode.exe" >nul
if %errorlevel%==0 (
  echo [..] ZCode is running. Quit it now ^(incl. tray icon^); this window restores automatically...
  timeout /t 3 /nobreak >nul
  goto waitquit
)
if not exist "app.asar.orig-backup" (
  echo [X] No app.asar.orig-backup found. Original version is already active?
  pause
  exit /b 1
)
if exist "app.asar" del /f /q "app.asar"
ren "app.asar.orig-backup" "app.asar"
if errorlevel 1 (
  echo [X] Restore failed. Please check antivirus lock and retry.
  pause
  exit /b 1
)
echo [OK] Original restored. Starting ZCode...
timeout /t 1 /nobreak >nul
start "" "..\ZCode.exe"
exit /b 0
