@echo off
set SCRIPT_DIR=%~dp0
set ROOT_DIR=%~dp0..\
"%SCRIPT_DIR%\.venv\Scripts\python.exe" "%ROOT_DIR%main.py" %*
