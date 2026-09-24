#!/bin/bash

if ! command -v ffmpeg &> /dev/null; then
  echo "→ Installing ffmpeg..."
  sudo apt install -y ffmpeg -q
fi

if [ ! -d "venv" ]; then
  echo "→ Creating virtual environment..."
  python3 -m venv venv
fi

echo "→ Installing dependencies..."
venv/bin/pip install -r requirements.txt -q

echo "→ Starting matercord (audio)..."
venv/bin/python app.py &

echo "→ Starting matercord (mp4)..."
venv/bin/python mp4.py &

echo "✓ Running on http://localhost:5010 — Press Ctrl+C to stop"

trap "echo '→ Shutting down...'; kill 0; exit 0" SIGINT SIGTERM
wait
