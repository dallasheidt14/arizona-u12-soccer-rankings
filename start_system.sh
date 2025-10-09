#!/bin/bash

echo "🚀 Starting Youth Soccer Rankings System..."

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install -r requirements_api.txt

# Start FastAPI backend
echo "🔧 Starting FastAPI backend on port 8000..."
python app.py &

# Wait a moment for backend to start
sleep 3

# Install Node dependencies (if not already installed)
if [ ! -d "node_modules" ]; then
    echo "📦 Installing Node.js dependencies..."
    npm install
fi

# Start React frontend
echo "🎨 Starting React frontend on port 3000..."
npm run dev &

echo ""
echo "✅ System is running!"
echo "🌐 Frontend: http://localhost:3000"
echo "🔧 Backend API: http://localhost:8000"
echo "📊 API Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop all services"
