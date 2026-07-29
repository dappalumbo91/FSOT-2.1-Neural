@echo off
REM Full connected mind — genetic brain + memory + live senses + speech.
REM Double-click this. Do NOT open .ps1 in the editor.
cd /d "%~dp0"
title FSOT Live Mind
echo.
echo ============================================================
echo   FSOT LIVE MIND — one connected organism
echo   (not a unit-test parade — brain stays online with senses)
echo ============================================================
echo.

where zig >nul 2>&1
if errorlevel 1 (
  echo ERROR: zig not on PATH
  pause
  exit /b 1
)

set "OUT=%TEMP%\fsot_mind_live.exe"
set "CACHE=%TEMP%\fsot_zig_cache_live"

echo Building...
zig build-exe -OReleaseFast "-femit-bin=%OUT%" --cache-dir "%CACHE%" --name fsot_mind_live src/main_mind.zig -lgdi32 -luser32 -lwinmm
if errorlevel 1 (
  echo BUILD FAILED
  pause
  exit /b 1
)

echo.
echo Starting live mind (~6 seconds of continuous experience)...
echo You should see structure, then mind t=30/300 ... with eps/enc/spikes growing.
echo Speakers may click briefly when the speech plant fires.
echo.
"%OUT%" mind
set ERR=%ERRORLEVEL%
echo.
if %ERR%==0 (
  echo ============================================================
  echo   FSOT_MIND_CONNECTED_OK
  echo ============================================================
) else (
  echo LIVE MIND FAILED exit=%ERR%
)
echo.
pause
exit /b %ERR%
