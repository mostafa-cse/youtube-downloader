# Setup script for Windows (PowerShell)
Write-Host "=== YT Downloader Environment Setup (Windows) ===" -ForegroundColor Cyan

# Check Python
try {
    $pyVer = python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
    Write-Host "✓ Found Python $pyVer" -ForegroundColor Green
} catch {
    Write-Host "❌ Error: Python is not found on PATH. Please install Python 3.10+." -ForegroundColor Red
    exit 1
}

# Create virtual environment if missing
if (-not (Test-Path "venv")) {
    Write-Host "Creating virtual environment in .\venv..."
    python -m venv venv
} else {
    Write-Host "✓ Existing virtual environment found at .\venv" -ForegroundColor Green
}

# Activate venv
Write-Host "Activating venv..."
& ".\venv\Scripts\Activate.ps1"

# Upgrade pip and install requirements
Write-Host "Installing dependencies..." -ForegroundColor Cyan
python -m pip install --upgrade pip
pip install -r requirements.txt pytest requests pillow

Write-Host "`n=== Setup Complete! ===" -ForegroundColor Green
Write-Host "To activate this environment anytime, run:"
Write-Host "  .\venv\Scripts\Activate.ps1"
Write-Host "To run tests:"
Write-Host "  pytest tests\ -v"
