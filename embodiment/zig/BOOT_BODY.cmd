@echo off
REM Double-click this file to boot FSOT mind body (Windows live senses).
cd /d "%~dp0"
title FSOT Body Boot
echo.
echo === FSOT body boot ===
echo Working dir: %CD%
echo.

where zig >nul 2>&1
if errorlevel 1 (
  echo ERROR: zig not found on PATH.
  echo Install Zig 0.15+ and reopen this window.
  pause
  exit /b 1
)

set "OUT=%TEMP%\fsot_mind_boot.exe"
set "CACHE=%TEMP%\fsot_zig_cache_boot"

echo [1/4] Building mind binary...
zig build-exe -OReleaseFast "-femit-bin=%OUT%" --cache-dir "%CACHE%" --name fsot_mind_boot src/main_mind.zig -lgdi32 -luser32 -lwinmm
if errorlevel 1 (
  echo BUILD FAILED
  pause
  exit /b 1
)
if not exist "%OUT%" (
  echo ERROR: binary not created: %OUT%
  pause
  exit /b 2
)

echo.
echo [2/4] host-senses (mic + display sample)...
"%OUT%" host-senses
if errorlevel 1 (
  echo HOST-SENSES FAILED
  pause
  exit /b 1
)

echo.
echo [3/4] plant smoke (body)...
"%OUT%" body
if errorlevel 1 (
  echo BODY FAILED
  pause
  exit /b 1
)

echo.
echo [4/4] FULL CONNECTED MIND (brain+memory+senses+speech)...
echo       This is the intelligent organism — not a unit test.
"%OUT%" mind
if errorlevel 1 (
  echo LIVE MIND FAILED
  pause
  exit /b 1
)

echo.
echo ==============================
echo  FSOT_MIND_CONNECTED_OK
echo ==============================
echo.
pause
