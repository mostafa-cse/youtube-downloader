#!/usr/bin/env bash
set -e

echo "=== YT Downloader Environment Setup (macOS / Linux) ==="

# Check Python 3
if ! command -v python3 &>/dev/null; then
    echo "❌ Error: python3 is not installed. Please install Python 3.10+."
    exit 1
fi

PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "✓ Found Python $PY_VER"

# Detect OS
OS_NAME="$(uname -s)"
echo "✓ Detected OS: $OS_NAME"

if [ "$OS_NAME" = "Linux" ]; then
    echo "ℹ Linux detected. If pywebview fails later, ensure libgtk-3-dev & libwebkit2gtk are installed."
fi

# Create virtual environment if missing
if [ ! -d "venv" ]; then
    echo "Creating virtual environment in ./venv..."
    python3 -m venv venv
else
    echo "✓ Existing virtual environment found at ./venv"
fi

# Activate venv
source venv/bin/activate

# Upgrade pip and install dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt pytest requests pillow

echo ""
echo "=== Setup Complete! ==="
echo "To activate this environment anytime, run:"
echo "  source venv/bin/activate"
echo "To run the automated tests:"
echo "  pytest tests/ -v"
