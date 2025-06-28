$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
& "$scriptDir\.venv\Scripts\python.exe" "$scriptDir\main.py" $args
