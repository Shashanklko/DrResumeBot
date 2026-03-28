# DrResumeBot Startup Script
# This script ensures dependencies are installed and starts both the Telegram Bot and Web API.

Write-Host ">>> Cleaning up any old processes..." -ForegroundColor Gray
taskkill /F /IM python.exe /T 2>$null | Out-Null
taskkill /F /IM py.exe /T 2>$null | Out-Null
Start-Sleep -Seconds 1

Write-Host ">>> Starting DrResumeBot Stack..." -ForegroundColor Cyan

$SERVER_DIR = "$PSScriptRoot\server"

# 1. Explicitly target system Python (v3.11)
# We avoid 'py' launcher because it defaults to 3.14 which is unstable.
$PYTHON_EXE = "python"
$testPy = & $PYTHON_EXE --version 2>$null
if ($LASTEXITCODE -ne 0) {
    # Fallback if 'python' name is missing (rare on this system)
    $PYTHON_EXE = "py -3.11"
    Write-Host "[INFO] Standard 'python' command failed. Trying 'py -3.11'..." -ForegroundColor Yellow
}

Write-Host "[INFO] Using Python 3.11 Stable Environment." -ForegroundColor Green

# 2. Check for dependencies
Write-Host "[INFO] Verifying dependencies..." -ForegroundColor Gray
& $PYTHON_EXE -m pip install -q -r "$SERVER_DIR\requirements.txt"

# 3. Check for .env file
if (-not (Test-Path "$SERVER_DIR\.env")) {
    Write-Host "[ERROR] server\.env file is missing!" -ForegroundColor Red
    Write-Host "Please copy server\.env.example to server\.env and add your API keys." -ForegroundColor White
    exit 1
}

# 4. Start the Application Stack
Write-Host "[SUCCESS] Launching DrResumeBot Master Application..." -ForegroundColor Green
Write-Host "Web Interface: http://localhost:10000" -ForegroundColor White
Write-Host "Telegram Bot: Online" -ForegroundColor White
Write-Host "-------------------------------------------" -ForegroundColor Gray

& $PYTHON_EXE "$SERVER_DIR\main.py"
