#!/bin/bash
# Development mode: runs backend + frontend separately with hot reload

echo "🔥 AppForge — Dev Mode"
echo "======================"

if [ -z "$GROQ_API_KEY" ] && [ -z "$(grep GROQ_API_KEY backend/.env)" ]; then
  echo "❌ GROQ_API_KEY not set"
  exit 1
fi

# Start backend in background
echo "Starting backend on :8000 ..."
cd backend
pip install -r requirements.txt -q
python server.py &
BACKEND_PID=$!
cd ..

# Start frontend dev server
echo "Starting frontend on :5173 ..."
cd frontend
npm install --silent
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "✅ AppForge running!"
echo "   Frontend: http://localhost:5173"
echo "   Backend:  http://localhost:8000"
echo "   API docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop both."

# Wait and cleanup
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT
wait
