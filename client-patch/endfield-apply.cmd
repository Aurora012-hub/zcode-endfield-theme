@echo off
chcp 65001 >nul
cd /d "%~dp0"
title ZCode Endfield Skin - Apply
echo ============================================
echo   ZCODE ENDFIELD INDUSTRIAL SKIN - APPLY
echo ============================================
echo.
if not exist "app.asar.endfield" (
  echo [X] app.asar.endfield not found. Run asar_patch.py first.
  pause
  exit /b 1
)
:waitquit
tasklist /FI "IMAGENAME eq ZCode.exe" 2>nul | find /I "ZCode.exe" >nul
if %errorlevel%==0 (
  echo [..] ZCode is running. Quit it now ^(incl. tray icon^); this window applies automatically...
  timeout /t 3 /nobreak >nul
  goto waitquit
)
if exist "app.asar.orig-backup" goto swap
ren "app.asar" "app.asar.orig-backup"
if errorlevel 1 (
  echo [X] Failed to backup app.asar. Nothing changed.
  pause
  exit /b 1
)
:swap
rem Re-apply scenario: orig-backup exists, current app.asar must be removed first
if exist "app.asar" del /f /q "app.asar"
if exist "app.asar" (
  echo [X] Cannot remove current app.asar ^(locked by antivirus?^). Nothing changed.
  pause
  exit /b 1
)
set TRY=0
:tryswap
ren "app.asar.endfield" "app.asar"
if not errorlevel 1 goto verify
set /a TRY+=1
echo [..] Rename blocked, likely antivirus scanning. Retry %TRY%/3...
if %TRY% GEQ 3 goto rollback
timeout /t 3 /nobreak >nul
goto tryswap
:verify
for %%F in ("app.asar") do set ASZ=%%~zF
if %ASZ% GEQ 1000000 goto done
echo [X] Swapped app.asar looks wrong ^(%ASZ% bytes^). Rolling back...
del /f /q "app.asar" 2>nul
goto restore
:rollback
echo [X] Apply failed after 3 retries. Rolling back to original...
:restore
if exist "app.asar" del /f /q "app.asar" 2>nul
if exist "app.asar.orig-backup" (
  ren "app.asar.orig-backup" "app.asar"
  if errorlevel 1 (
    echo [X] ROLLBACK FAILED - restore manually: ren app.asar.orig-backup app.asar
    pause
    exit /b 1
  )
  echo [!] Rolled back to original. app.asar.endfield kept for retry.
)
pause
exit /b 1
:done
echo [OK] Endfield skin applied. Starting ZCode...
timeout /t 1 /nobreak >nul
start "" "..\ZCode.exe"
exit /b 0
