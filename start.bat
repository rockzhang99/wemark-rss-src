@echo off
title wemark-rss start (Windows)

set PY=python
where python >nul 2>nul
if errorlevel 1 (
    where python3 >nul 2>nul
    if not errorlevel 1 set PY=python3
)

set PW_DIR=%LOCALAPPDATA%\ms-playwright
dir /b "%PW_DIR%\webkit-*" >nul 2>nul
if errorlevel 1 (
    echo [INFO] Playwright WebKit not found, installing (needs network)...
    %PY% -m playwright install webkit
) else (
    echo [OK] Playwright WebKit detected.
)

%PY% main.py -job True -init True
