#!/bin/bash

# Start Whale Scanner Web UI

echo "=================================="
echo "🐋 Starting Whale Scanner Web UI"
echo "=================================="
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found!"
    echo "   Please run: ./setup.sh"
    exit 1
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Check if Flask is installed
if ! python -c "import flask" 2>/dev/null; then
    echo "⚠️  Flask not found. Installing web dependencies..."
    pip install Flask Flask-CORS Flask-SocketIO python-socketio eventlet
fi

# Check if config exists
if [ ! -f "config.yaml" ]; then
    echo "❌ config.yaml not found!"
    exit 1
fi

# Create logs directory
mkdir -p logs

# Display instructions
echo ""
echo "✓ Starting web server..."
echo ""
echo "======================================"
echo "📊 Web Dashboard: http://localhost:5000"
echo "======================================"
echo ""
echo "⚠️  IMPORTANT:"
echo "   1. Make sure IBKR TWS or Gateway is running"
echo "   2. API connections must be enabled"
echo "   3. Use the web UI to start/stop scanner"
echo ""
echo "Press Ctrl+C to stop the server"
echo "======================================"
echo ""

# Start Flask app
python web_app.py
