# ========================================
# Arbitrage System - Automated Startup Script
# ========================================
# This script automatically starts both the Python server and C++ detector
# in separate PowerShell windows with proper initialization checks.

# CLAUDE_FIX: Change to project root (parent of scripts directory)
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  ARBITRAGE SYSTEM STARTUP" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan
Write-Host "Project root: $projectRoot`n" -ForegroundColor Gray

# CLAUDE_FIX: Verify prerequisites exist
Write-Host "[1/5] Verifying prerequisites..." -ForegroundColor Cyan

# Check virtual environment
$venvActivatePath = "venv\Scripts\Activate.ps1"
if (-not (Test-Path $venvActivatePath)) {
    Write-Host "[ERROR] Virtual environment not found at: $venvActivatePath" -ForegroundColor Red
    Write-Host "Please create a virtual environment first:" -ForegroundColor Yellow
    Write-Host "  python -m venv venv" -ForegroundColor Yellow
    Write-Host "  .\venv\Scripts\Activate.ps1" -ForegroundColor Yellow
    Write-Host "  pip install -r requirements.txt" -ForegroundColor Yellow
    Read-Host "`nPress Enter to exit"
    exit 1
}
Write-Host "  [OK] Virtual environment found" -ForegroundColor Green

# Check C++ executable
$cppExePath = "cpp\build\arbitrage_detector.exe"
if (-not (Test-Path $cppExePath)) {
    Write-Host "[ERROR] C++ executable not found at: $cppExePath" -ForegroundColor Red
    Write-Host "Please compile the C++ code first:" -ForegroundColor Yellow
    Write-Host "  .\scripts\compile.ps1" -ForegroundColor Yellow
    Read-Host "`nPress Enter to exit"
    exit 1
}
Write-Host "  [OK] C++ executable found" -ForegroundColor Green

# CLAUDE_FIX: Check if port 5001 is already in use
Write-Host "`n[2/5] Checking port availability..." -ForegroundColor Cyan
$portInUse = $false
try {
    $existingConnection = Get-NetTCPConnection -LocalPort 5001 -ErrorAction SilentlyContinue | Where-Object { $_.State -eq 'Listen' }
    if ($existingConnection) {
        $portInUse = $true
        $processId = $existingConnection.OwningProcess
        $processName = (Get-Process -Id $processId -ErrorAction SilentlyContinue).ProcessName

        Write-Host "  [WARNING] Port 5001 is already in use" -ForegroundColor Yellow
        Write-Host "  Process: $processName (PID: $processId)" -ForegroundColor Yellow

        $response = Read-Host "  Do you want to kill this process? (y/n)"
        if ($response -eq 'y' -or $response -eq 'Y') {
            try {
                Stop-Process -Id $processId -Force
                Write-Host "  [OK] Process terminated successfully" -ForegroundColor Green
                Start-Sleep -Seconds 2  # Wait for port to be released
                $portInUse = $false
            } catch {
                Write-Host "  [ERROR] Failed to terminate process: $_" -ForegroundColor Red
                Read-Host "`nPress Enter to exit"
                exit 1
            }
        } else {
            Write-Host "  [ERROR] Cannot start system with port 5001 occupied" -ForegroundColor Red
            Write-Host "  Please manually stop the process or change PORT in config/network.py" -ForegroundColor Yellow
            Read-Host "`nPress Enter to exit"
            exit 1
        }
    } else {
        Write-Host "  [OK] Port 5001 is available" -ForegroundColor Green
    }
} catch {
    # If Get-NetTCPConnection fails, assume port is available
    Write-Host "  [OK] Port 5001 appears to be available" -ForegroundColor Green
}

# CLAUDE_FIX: Start Python server in new window
Write-Host "`n[3/5] Starting Python server..." -ForegroundColor Cyan

$pythonScript = @"
Set-Location '$projectRoot'
& .\venv\Scripts\Activate.ps1
`$Host.UI.RawUI.WindowTitle = '=== PYTHON SERVER ==='
Write-Host '========================================' -ForegroundColor Cyan
Write-Host '  PYTHON SERVER STARTING...' -ForegroundColor Cyan
Write-Host '========================================' -ForegroundColor Cyan
`$env:PYTHONPATH = '$projectRoot'
python python\main.py
"@

$pythonScriptPath = Join-Path $env:TEMP "arbitrage_python_startup.ps1"
$pythonScript | Out-File -FilePath $pythonScriptPath -Encoding UTF8

try {
    $pythonProcess = Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", $pythonScriptPath -PassThru
    Write-Host "  [OK] Python server window opened (PID: $($pythonProcess.Id))" -ForegroundColor Green
} catch {
    Write-Host "  [ERROR] Failed to start Python server: $_" -ForegroundColor Red
    Read-Host "`nPress Enter to exit"
    exit 1
}

# CLAUDE_FIX: Wait for Python server to start listening on port 5001
Write-Host "`n[4/5] Waiting for Python server to be ready..." -ForegroundColor Cyan
$timeout = 20  # seconds
$elapsed = 0
$serverReady = $false

Write-Host "  Checking" -NoNewline
while ($elapsed -lt $timeout) {
    try {
        $listening = Get-NetTCPConnection -LocalPort 5001 -State Listen -ErrorAction SilentlyContinue
        if ($listening) {
            $serverReady = $true
            Write-Host ""
            Write-Host "  [OK] Python server is listening on port 5001" -ForegroundColor Green
            break
        }
    } catch {
        # Port not yet listening, continue waiting
    }

    Write-Host "." -NoNewline
    Start-Sleep -Seconds 1
    $elapsed++
}

if (-not $serverReady) {
    Write-Host ""
    Write-Host "  [ERROR] Python server did not start within $timeout seconds" -ForegroundColor Red
    Write-Host "  Check the Python server window for error messages" -ForegroundColor Yellow
    Write-Host "  Stopping Python server process..." -ForegroundColor Yellow
    try {
        Stop-Process -Id $pythonProcess.Id -Force -ErrorAction SilentlyContinue
    } catch {}
    Read-Host "`nPress Enter to exit"
    exit 1
}

# Add small delay to ensure server is fully initialized
Start-Sleep -Seconds 2

# CLAUDE_FIX: Start C++ detector in new window
Write-Host "`n[5/5] Starting C++ detector..." -ForegroundColor Cyan

$cppScript = @"
Set-Location '$projectRoot'
`$Host.UI.RawUI.WindowTitle = '=== C++ DETECTOR ==='
Write-Host '========================================' -ForegroundColor Cyan
Write-Host '  C++ DETECTOR STARTING...' -ForegroundColor Cyan
Write-Host '========================================' -ForegroundColor Cyan
.\cpp\build\arbitrage_detector.exe
"@

$cppScriptPath = Join-Path $env:TEMP "arbitrage_cpp_startup.ps1"
$cppScript | Out-File -FilePath $cppScriptPath -Encoding UTF8

try {
    $cppProcess = Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", $cppScriptPath -PassThru
    Write-Host "  [OK] C++ detector window opened (PID: $($cppProcess.Id))" -ForegroundColor Green
} catch {
    Write-Host "  [ERROR] Failed to start C++ detector: $_" -ForegroundColor Red
    Write-Host "  Stopping Python server..." -ForegroundColor Yellow
    try {
        Stop-Process -Id $pythonProcess.Id -Force -ErrorAction SilentlyContinue
    } catch {}
    Read-Host "`nPress Enter to exit"
    exit 1
}

# CLAUDE_FIX: Print success message
Write-Host "`n========================================" -ForegroundColor Green
Write-Host "  SISTEMA AVVIATO CON SUCCESSO!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Due finestre aperte:" -ForegroundColor Cyan
Write-Host "  1. Python Server  (PID: $($pythonProcess.Id))" -ForegroundColor White
Write-Host "  2. C++ Detector   (PID: $($cppProcess.Id))" -ForegroundColor White
Write-Host ""
Write-Host "Per fermare il sistema:" -ForegroundColor Yellow
Write-Host "  - Premi CTRL+C in entrambe le finestre, oppure" -ForegroundColor Yellow
Write-Host "  - Chiudi entrambe le finestre PowerShell" -ForegroundColor Yellow
Write-Host ""
Write-Host "Monitoraggio:" -ForegroundColor Cyan
Write-Host "  - Finestra Python: mostra WebSocket streaming e connessioni" -ForegroundColor White
Write-Host "  - Finestra C++: mostra rilevamento arbitraggi in tempo reale" -ForegroundColor White
Write-Host ""
Write-Host "Output salvato in:" -ForegroundColor Cyan
Write-Host "  - output/snapshots/Initial_Snapshot_Binance.csv" -ForegroundColor White
Write-Host "  - output/snapshots/Initial_Snapshot_OKX.csv" -ForegroundColor White
Write-Host ""
Write-Host "========================================`n" -ForegroundColor Green

# Keep this window open to show the success message
Write-Host "Questo script puo' essere chiuso in sicurezza." -ForegroundColor Gray
Write-Host "Le finestre Python e C++ continueranno a funzionare." -ForegroundColor Gray
Read-Host "`nPremi Enter per chiudere questo script"
