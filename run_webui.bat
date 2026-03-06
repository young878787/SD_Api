@echo off
cd /d "%~dp0"
call .venv\Scripts\activate.bat

set "SD_URL=http://127.0.0.1:7878"
set "UI_PORT=7801"

echo [Prompt Editor 啟動設定]
set /p SD_INPUT=SD WebUI URL (直接 Enter 使用預設 %SD_URL%): 
if not "%SD_INPUT%"=="" set "SD_URL=%SD_INPUT%"

set /p PORT_INPUT=Gradio Port (直接 Enter 使用預設 %UI_PORT%): 
if not "%PORT_INPUT%"=="" set "UI_PORT=%PORT_INPUT%"

echo.
echo 啟動中... SD_URL=%SD_URL% , PORT=%UI_PORT%
python prompt_editor_ui.py --sd-url "%SD_URL%" --port %UI_PORT% --auto-port
pause
