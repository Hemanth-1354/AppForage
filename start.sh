#!/bin/bash

# AppForge Startup Script
# Starts both backend and frontend

set -e

echo "🔥 AppForge — NL → App Compiler"
echo "================================"

# Check API key
if [ -z "$GROQ_API_KEY" ] && [ -z "$(grep GROQ_API_KEY backend/.env)" ]; then
  echo "❌ Error: GROQ_API_KEY not set"
  echo "   Add it to backend/.env or export it."
  exit 1
fi

echo "✅ API key found"

# Install backend deps
echo ""
echo "📦 Installing backend dependencies..."
cd backend
pip install -r requirements.txt -q
cd ..

# Install + build frontend
echo "📦 Installing frontend dependencies..."
cd frontend
npm install --silent
echo "🏗️  Building frontend..."
npm run build --silent
cd ..

echo ""
echo "🚀 Starting AppForge backend server..."
echo "   URL: http://localhost:8000"
echo ""
echo "Press Ctrl+C to stop."
echo ""

cd backend
python server.py
