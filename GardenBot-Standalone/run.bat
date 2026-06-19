@echo off
setlocal
cd /d "%~dp0"

rem Use the Python launcher if present, otherwise "python"
where py >nul 2>nul && (set PY=py) || (set PY=python)

echo Installing/updating dependencies (first run only, needs internet)...
%PY% -m pip install -q -r requirements.txt
if errorlevel 1 (
  echo.
  echo Dependency install failed. Make sure Python 3.10+ is installed and on PATH.
  echo.
  pause
  exit /b 1
)

echo.
echo ============================================================
echo  GardenBot - make sure Wizard101 is OPEN, logged in, and
echo  your character is STANDING IN YOUR GARDEN bed.
echo.
echo   CTRL+ALT+G = plant     CTRL+ALT+S = scan soil     CTRL+ALT+K = quit
echo ============================================================
echo.

%PY% plant_bot.py

echo.
pause
