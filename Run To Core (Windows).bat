@echo off
REM Double-click this to start The Run To Core.
REM Windows does not come with Python, so check for it before blaming the tool.

setlocal
cd /d "%~dp0"

set PY=
where py >nul 2>&1 && set PY=py
if "%PY%"=="" (where python >nul 2>&1 && set PY=python)

if "%PY%"=="" (
    echo.
    echo   Python is not installed, and this tool needs it.
    echo.
    echo   Get it from   https://www.python.org/downloads/
    echo   On the first screen of the installer, tick
    echo   "Add python.exe to PATH" before pressing Install.
    echo.
    echo   Then double-click this file again.
    echo.
    pause
    exit /b 1
)

%PY% core_run.py --app %*
if errorlevel 1 pause
