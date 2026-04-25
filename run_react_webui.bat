@echo off
chcp 65001 >nul
title Prompt Editor Pro (React + FastAPI)
color 0B

echo =========================================
echo    Starting Prompt Editor Pro
echo =========================================
echo.

set /p SD_PORT="Please enter SD WebUI Port [Default 9001]: "
if "%SD_PORT%"=="" set SD_PORT=9001

set /p VITE_PORT_INPUT="Please enter Frontend Vite Port [Default 15002]: "
if "%VITE_PORT_INPUT%"=="" set VITE_PORT_INPUT=15002

set SD_WEBUI_URL=http://127.0.0.1:%SD_PORT%
set VITE_PORT=%VITE_PORT_INPUT%
set BACKEND_PORT=15001
set VITE_BACKEND_PORT=15001

echo.
echo SD WebUI URL is set to: %SD_WEBUI_URL%
echo Frontend Vite will run on: %VITE_PORT%
echo Backend API will run on: %BACKEND_PORT%
echo.

echo Launching both Backend and Frontend in this window...
echo Press CTRL+C to stop both servers.
echo.

cd frontend
call npm run dev

