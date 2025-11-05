#!/bin/bash

# Whale Scanner Configuration Web UI - Startup Script

echo "========================================"
echo "Whale Scanner Configuration Web UI"
echo "========================================"
echo ""

# Check if PostgreSQL is running
echo "1. Checking PostgreSQL..."
if pg_isready -q 2>/dev/null; then
    echo "   ✓ PostgreSQL is running"
else
    echo "   ✗ PostgreSQL is not running"
    echo ""
    echo "   Please start PostgreSQL first:"
    echo ""
    echo "   On macOS with Homebrew:"
    echo "   → brew services start postgresql@14"
    echo "   or"
    echo "   → brew services start postgresql"
    echo ""
    echo "   On Linux:"
    echo "   → sudo systemctl start postgresql"
    echo "   or"
    echo "   → sudo service postgresql start"
    echo ""
    echo "   Then run this script again."
    exit 1
fi

# Check if database exists
echo "2. Checking database..."
if psql -lqt | cut -d \| -f 1 | grep -qw whale_scanner 2>/dev/null; then
    echo "   ✓ Database 'whale_scanner' exists"
else
    echo "   ✗ Database 'whale_scanner' not found"
    echo ""
    echo "   Please initialize the database:"
    echo "   → python database/setup_postgres.py"
    echo ""
    exit 1
fi

# Start web UI
echo "3. Starting web server..."
echo ""
echo "========================================"
echo "Web UI will be available at:"
echo "http://localhost:5000"
echo "========================================"
echo ""
echo "Press Ctrl+C to stop"
echo ""

python web_config_ui.py
