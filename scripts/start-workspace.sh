#!/bin/bash

# Start GatheRing with Workspace (Phase 7.1)

echo "🚀 Starting GatheRing API and Dashboard..."
echo ""

# Kill any existing servers
pkill -f uvicorn 2>/dev/null
pkill -f vite 2>/dev/null
sleep 1

# Start API server
echo "📡 Starting API server on http://localhost:8000..."
cd /home/loc/workspace/gathering
source venv/bin/activate
uvicorn gathering.api:app --reload --port 8000 > /tmp/gathering-api.log 2>&1 &
API_PID=$!

# Wait for API to start
sleep 3

# Start dashboard
echo "🎨 Starting Dashboard on http://localhost:3000..."
cd /home/loc/workspace/gathering/dashboard
npm run dev > /tmp/gathering-dashboard.log 2>&1 &
DASH_PID=$!

# Wait for dashboard to start
sleep 3

echo ""
echo "✅ GatheRing is running!"
echo ""
echo "📍 URLs:"
echo "   API:       http://localhost:8000"
echo "   Dashboard: http://localhost:3000"
echo "   Workspace: http://localhost:3000/workspace/1"
echo ""
echo "📊 API Endpoints:"
echo "   http://localhost:8000/docs         - Swagger UI"
echo "   http://localhost:8000/workspace/1/info"
echo "   http://localhost:8000/workspace/1/git/status"
echo "   http://localhost:8000/workspace/1/git/commits"
echo ""
echo "📋 Logs:"
echo "   API:       tail -f /tmp/gathering-api.log"
echo "   Dashboard: tail -f /tmp/gathering-dashboard.log"
echo ""
echo "🛑 To stop:"
echo "   kill $API_PID $DASH_PID"
echo "   or: pkill -f uvicorn && pkill -f vite"
echo ""
