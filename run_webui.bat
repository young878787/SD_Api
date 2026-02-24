@echo off
cd /d "%~dp0"
call .venv\Scripts\activate.bat
python prompt_editor_ui.py
pause
