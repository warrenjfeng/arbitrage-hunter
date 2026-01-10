#!/bin/bash

# Quick start script for demo
echo "🚀 Starting Arbitrage Hunter Demo"
echo "=================================="
echo ""

# Check if MongoDB is connected
echo "📊 Checking database connection..."
python3 -c "from config import get_db; db = get_db(); print('✅ MongoDB connected')" 2>/dev/null || {
    echo "❌ MongoDB connection failed. Check your .env file."
    exit 1
}

# Generate dummy data
echo ""
echo "🎲 Generating dummy data..."
python3 generate_dummy_data.py

# Start the dashboard
echo ""
echo "🌐 Starting dashboard server..."
echo "   Dashboard will be available at: http://localhost:5000"
echo "   Press Ctrl+C to stop"
echo ""

python3 app.py

