@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
title Prompt Editor Pro (React + FastAPI)
color 0B
cd /d "%~dp0"

echo =========================================
echo    Starting Prompt Editor Pro
echo =========================================
echo.

REM -- Auto-detect Stable Diffusion WebUI Port --
echo [Auto-Detect] Scanning for Stable Diffusion WebUI...
echo.

set "_SD_PORT="
for %%P in (7860 7861 7862 7863 7864 7865 9001 9002 9003 8080 8888 18787 8787) do (
    if not defined _SD_PORT (
        for /f %%A in ('curl -s -o nul -w "%%{http_code}" --connect-timeout 2 http://127.0.0.1:%%P/sdapi/v1/sd-models 2^>nul') do (
            if "%%A"=="200" (
                set "_SD_PORT=%%P"
                echo   [OK] Found SD WebUI on port %%P
            )
        )
    )
)

if not defined _SD_PORT (
    echo   [!!] No running SD WebUI found.
    echo        Checked: 7860-7865, 9001-9003, 8080, 8888, 18787, 8787
    echo        Falling back to default port 7860
    set "_SD_PORT=7860"
)

REM -- Set all ports automatically --
set "SD_WEBUI_URL=http://127.0.0.1:!_SD_PORT!"
set "VITE_PORT=15002"
set "BACKEND_PORT=15001"
set "VITE_BACKEND_PORT=15001"

echo.
echo  -----------------------------------------
echo    SD WebUI  : !SD_WEBUI_URL!
echo    Frontend  : http://127.0.0.1:!VITE_PORT!
echo    Backend   : http://127.0.0.1:!BACKEND_PORT!
echo  -----------------------------------------
echo.

REM -- Pass env vars out of setlocal, then restore workdir --
endlocal & (
    set "SD_WEBUI_URL=%SD_WEBUI_URL%"
    set "VITE_PORT=%VITE_PORT%"
    set "BACKEND_PORT=%BACKEND_PORT%"
    set "VITE_BACKEND_PORT=%VITE_BACKEND_PORT%"
)
cd /d "%~dp0"

echo Launching Backend + Frontend...
echo Press CTRL+C to stop all servers.
echo.

cd frontend
call npm run dev
