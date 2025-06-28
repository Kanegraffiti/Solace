$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$rootDir = Join-Path $scriptDir ".."
& "$scriptDir\.venv\Scripts\python.exe" (Join-Path $rootDir "main.py") $args
