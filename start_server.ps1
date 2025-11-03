# MMO Pacman Server Startup Script
# This script automatically activates the virtual environment and starts the server

Write-Host "Starting MMO Pacman Server..." -ForegroundColor Green
Write-Host "Activating virtual environment..." -ForegroundColor Yellow

# Navigate to the project directory
Set-Location -Path $PSScriptRoot

# Activate virtual environment
& ".\.venv\Scripts\Activate.ps1"

if ($LASTEXITCODE -eq 0) {
    Write-Host "Virtual environment activated successfully!" -ForegroundColor Green
    Write-Host "Starting Python server..." -ForegroundColor Yellow
    python app.py
} else {
    Write-Host "Failed to activate virtual environment!" -ForegroundColor Red
    Write-Host "Please ensure the virtual environment exists in .\.venv\" -ForegroundColor Yellow
    pause
}