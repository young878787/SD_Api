@echo off
chcp 65001 >nul
title Prompt Editor Pro (React + FastAPI)
color 0B

echo =========================================
echo    Starting Prompt Editor Pro
echo =========================================
echo.

set /p SD_PORT="Please enter SD WebUI Port [Default 8888]: "
if "%SD_PORT%"=="" set SD_PORT=8888

set SD_WEBUI_URL=http://127.0.0.1:%SD_PORT%

echo.
echo SD WebUI URL is set to: %SD_WEBUI_URL%
echo.

echo Launching both Backend and Frontend in this window...
echo Press CTRL+C to stop both servers.
echo.

cd frontend
call npm run dev
