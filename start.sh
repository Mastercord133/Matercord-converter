#!/bin/bash

if ! command -v ffmpeg &> /dev/null; then
  echo "â†’ Installing ffmpeg..."
  sudo apt install -y ffmpeg -q
fi

if [ ! -d "venv" ]; then
  echo "â†’ Creating virtual environment..."
  python3 -m venv venv
fi

echo "â†’ Installing dependencies..."
venv/bin/pip install -r requirements.txt -q

echo "â†’ Starting matercord..."
venv/bin/python app.py


