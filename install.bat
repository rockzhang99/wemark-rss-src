@echo off
title wemark-rss install (Windows)
echo ============================================
echo   wemark-rss first-time install (Windows)
echo ============================================

set PY=python
where python >nul 2>nul
if errorlevel 1 (
    where python3 >nul 2>nul
    if not errorlevel 1 (set PY=python3) else (
        echo [ERROR] Python not found. Install Python 3.10+ and add to PATH.
        pause
        exit /b 1
    )
)

echo.
echo [1/4] Installing Python deps (requirements.txt)...
%PY% -m pip install --upgrade pip
%PY% -m pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] pip install failed. Check network and retry.
    pause
    exit /b 1
)

echo.
echo [2/4] Installing Playwright browser (webkit, agent default)...
%PY% -m playwright install webkit
echo   (Optional for PDF export: %PY% -m playwright install chromium)

echo.
echo [3/4] Init config...
if not exist config.yaml (
    if exist config.example.yaml (
        copy config.example.yaml config.yaml >nul
        echo   config.yaml generated. Edit deploy/upload sections as needed.
    ) else (
        echo   config.example.yaml not found, skipped.
    )
) else (
    echo   config.yaml already exists, skipped.
)

echo.
echo [4/4] Done!
echo Start options:
echo   1) double-click start.bat
echo   2) command: %PY% main.py -job True -init True
echo.
echo For agent to cloud upload, set in config.yaml:
echo   deploy.role=agent and upload.server / ak / sk
pause
