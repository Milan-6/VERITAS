<#
.SYNOPSIS
    Clean Shutdown Script for VERITAS on Windows PowerShell.
.DESCRIPTION
    Safely terminates Uvicorn/FastAPI backend on port 8000, Next.js frontend on port 3000,
    flushes SQLite WAL checkpoints, and cleans up Qdrant locks.
#>

$ErrorActionPreference = "SilentlyContinue"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  VERITAS Clean Shutdown (PowerShell)" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

$ports = @(8000, 3000)

foreach ($port in $ports) {
    $service = if ($port -eq 8000) { "FastAPI Backend" } else { "Next.js Frontend" }
    Write-Host "[*] Checking $service on port $port..." -ForegroundColor Yellow
    
    # Identify listening process IDs
    $connections = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    if ($connections) {
        foreach ($conn in $connections) {
            $pidToKill = $conn.OwningProcess
            if ($pidToKill -gt 0) {
                Write-Host "    Found process PID $pidToKill listening on port $port. Terminating..." -ForegroundColor Yellow
                Stop-Process -Id $pidToKill -Force -ErrorAction SilentlyContinue
                Write-Host "    [✓] Terminated PID $pidToKill" -ForegroundColor Green
            }
        }
    } else {
        # Fallback to netstat if Get-NetTCPConnection lacks CIM access
        $netstatLines = netstat -ano | Select-String ":$port\s"
        foreach ($line in $netstatLines) {
            $tokens = -split $line.Line.Trim()
            if ($tokens.Count -ge 5 -and $tokens[3] -eq "LISTENING") {
                $pidVal = [int]$tokens[4]
                if ($pidVal -gt 0) {
                    Write-Host "    Terminating PID $pidVal (from netstat)..." -ForegroundColor Yellow
                    taskkill /F /PID $pidVal | Out-Null
                    Write-Host "    [✓] Terminated PID $pidVal" -ForegroundColor Green
                }
            }
        }
    }
}

# Stop any dangling runner processes
Write-Host "[*] Checking for lingering node / python dev server instances..." -ForegroundColor Yellow
Get-Process -Name node -ErrorAction SilentlyContinue | Where-Object { $_.Path -like "*Project-1*" } | Stop-Process -Force -ErrorAction SilentlyContinue

# SQLite WAL Flush
$dbPath = "$PSScriptRoot\..\veritas.db"
if (Test-Path $dbPath) {
    Write-Host "[*] Flushing SQLite WAL checkpoint on veritas.db..." -ForegroundColor Yellow
    $pyExe = "$PSScriptRoot\..\venv\Scripts\python.exe"
    if (Test-Path $pyExe) {
        & $pyExe -c "import sqlite3; conn = sqlite3.connect(r'$dbPath'); cur = conn.cursor(); cur.execute('PRAGMA wal_checkpoint(TRUNCATE);'); print('    [✓] WAL checkpoint flushed:', cur.fetchone()); conn.close()"
    }
}

# Clear stale vector lock
$lockPath = "$PSScriptRoot\..\data\qdrant\.lock"
if (Test-Path $lockPath) {
    Write-Host "[*] Removing stale Qdrant lock file..." -ForegroundColor Yellow
    Remove-Item -Path $lockPath -Force -ErrorAction SilentlyContinue
    Write-Host "    [✓] Stale vector lock removed." -ForegroundColor Green
}

# Final port verification
Write-Host "[*] Verifying port status..." -ForegroundColor Yellow
foreach ($port in $ports) {
    $conns = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    if ($conns) {
        Write-Host "    [!] Warning: Port $port still occupied." -ForegroundColor Red
    } else {
        Write-Host "    [✓] Port $port is completely free." -ForegroundColor Green
    }
}

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  VERITAS services successfully stopped." -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan
