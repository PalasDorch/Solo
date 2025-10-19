# Solomon Interface Launcher
# Starts GPT proxy and Vite UI

$ErrorActionPreference = "Stop"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Solomon Interface Launcher" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

$SolomonRoot = "S:\Solomon"
$InterfaceRoot = "$SolomonRoot\src\interface"
$ProxyDir = "$InterfaceRoot\proxy"
$UIDir = "$InterfaceRoot\ui"
$VenvPath = "$SolomonRoot\.venv"
$PythonExe = "$VenvPath\Scripts\python.exe"
$PipExe = "$VenvPath\Scripts\pip.exe"

# Check virtual environment
if (-not (Test-Path $PythonExe)) {
    Write-Host "ERROR: Virtual environment not found at $VenvPath" -ForegroundColor Red
    Write-Host "Please create it first: python -m venv $VenvPath" -ForegroundColor Yellow
    exit 1
}

# Check proxy directory
if (-not (Test-Path $ProxyDir)) {
    Write-Host "ERROR: Proxy directory not found at $ProxyDir" -ForegroundColor Red
    exit 1
}

# Check UI directory
if (-not (Test-Path $UIDir)) {
    Write-Host "ERROR: UI directory not found at $UIDir" -ForegroundColor Red
    exit 1
}

# Install proxy dependencies
Write-Host "Installing proxy dependencies..." -ForegroundColor Yellow
Set-Location $ProxyDir
& $PipExe install -q -r requirements.txt

# Check proxy .env
if (-not (Test-Path "$ProxyDir\.env")) {
    Write-Host "WARNING: Proxy .env not found. Using defaults." -ForegroundColor Yellow
    Write-Host "Create $ProxyDir\.env with your OPENAI_API_KEY" -ForegroundColor Yellow
}

# Start proxy in background
Write-Host ""
Write-Host "Starting GPT Proxy on http://127.0.0.1:8601..." -ForegroundColor Green
$ProxyJob = Start-Job -ScriptBlock {
    param($PythonExe, $ProxyDir)
    Set-Location $ProxyDir
    & $PythonExe -m uvicorn proxy_server:app --host 127.0.0.1 --port 8601
} -ArgumentList $PythonExe, $ProxyDir

Start-Sleep -Seconds 2

# Check if proxy started
if ($ProxyJob.State -ne "Running") {
    Write-Host "ERROR: Proxy failed to start" -ForegroundColor Red
    Receive-Job $ProxyJob
    exit 1
}

Write-Host "✓ Proxy running (Job ID: $($ProxyJob.Id))" -ForegroundColor Green

# Start UI
Write-Host ""
Write-Host "Starting Vite UI..." -ForegroundColor Green
Set-Location $UIDir

# Install UI dependencies if needed
if (-not (Test-Path "$UIDir\node_modules")) {
    Write-Host "Installing UI dependencies..." -ForegroundColor Yellow
    npm install
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Services Running:" -ForegroundColor Cyan
Write-Host "  - GPT Proxy: http://127.0.0.1:8601" -ForegroundColor White
Write-Host "  - Bridge API: http://127.0.0.1:8500 (start separately)" -ForegroundColor White
Write-Host "  - UI: Starting..." -ForegroundColor White
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press Ctrl+C to stop all services" -ForegroundColor Yellow
Write-Host ""

# Start UI (foreground)
try {
    npm run dev
} finally {
    # Cleanup
    Write-Host ""
    Write-Host "Stopping services..." -ForegroundColor Yellow
    Stop-Job $ProxyJob
    Remove-Job $ProxyJob
    Write-Host "✓ All services stopped" -ForegroundColor Green
}

