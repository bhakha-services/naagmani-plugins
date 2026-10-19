@echo off
setlocal
set "SCRIPT_DIR=%~dp0.."
set "PYTHONNOUSERSITE=1"
set "PYTHONDONTWRITEBYTECODE=1"
set "PYTHONUNBUFFERED=1"
set "TLDEXTRACT_PUBLIC_SUFFIX_LIST_URLS="
set "PYTHONPATH=%SCRIPT_DIR%;%SCRIPT_DIR%\vendor;%SCRIPT_DIR%\site-packages;%PYTHONPATH%"

if exist "%SCRIPT_DIR%\runtime\python.exe" (
    set "PY_BIN=%SCRIPT_DIR%\runtime\python.exe"
) else (
    set "PY_BIN=python"
)

"%PY_BIN%" -s "%SCRIPT_DIR%\main.py" %*
endlocal
