#!/bin/bash

# IBKR Whale Options Scanner - Setup Script
# For Evermont Trading

echo "=================================="
echo "🐋 IBKR Whale Scanner Setup"
echo "=================================="
echo ""

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | grep -oP '\d+\.\d+')
required_version="3.8"

if (( $(echo "$python_version < $required_version" | bc -l) )); then
    echo "❌ Python 3.8+ required. Found: $python_version"
    exit 1
fi
echo "✓ Python $python_version found"
echo ""

# Create virtual environment
echo "Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi
echo ""

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate
echo "✓ Virtual environment activated"
echo ""

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip setuptools wheel
echo "✓ Pip upgraded"
echo ""

# Install dependencies
echo "Installing dependencies..."
echo "This may take a few minutes..."

# Try to install ta-lib separately (often fails)
echo ""
echo "Attempting to install TA-Lib..."
pip install ta-lib 2>/dev/null
if [ $? -ne 0 ]; then
    echo "⚠  TA-Lib installation failed (optional dependency)"
    echo "   To install TA-Lib:"
    echo "   Ubuntu/Debian: sudo apt-get install libta-lib-dev"
    echo "   macOS: brew install ta-lib"
    echo "   Then run: pip install ta-lib"
    echo ""
    echo "   Continuing without TA-Lib..."
fi

# Install other dependencies
echo ""
echo "Installing other dependencies..."
pip install ib_insync pandas numpy scipy sqlalchemy python-dotenv requests aiohttp python-dateutil pytz colorlog tabulate pyyaml

echo ""
echo "✓ Dependencies installed"
echo ""

# Create directories
echo "Creating directories..."
mkdir -p data logs
echo "✓ Directories created"
echo ""

# Check if config exists
if [ ! -f "config.yaml" ]; then
    echo "⚠  config.yaml not found!"
    echo "   Please ensure config.yaml is in the current directory"
else
    echo "✓ config.yaml found"
fi
echo ""

# Summary
echo "=================================="
echo "✓ Setup Complete!"
echo "=================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Start IBKR TWS or IB Gateway"
echo "   - Enable API connections in settings"
echo "   - Set correct port (7497 for paper, 7496 for live)"
echo ""
echo "2. Activate the virtual environment (if not already active):"
echo "   source venv/bin/activate"
echo ""
echo "3. Edit config.yaml to customize settings"
echo "   - Set your watchlist"
echo "   - Configure filters"
echo ""
echo "4. Run the scanner:"
echo "   python scanner.py --mode once"
echo ""
echo "5. For continuous scanning:"
echo "   python scanner.py --mode continuous"
echo ""
echo "=================================="
echo "🐋 Happy Whale Hunting!"
echo "=================================="
