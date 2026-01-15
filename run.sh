#!/bin/bash

# Travel Concierge Agent - Run Script (assumes setup already done)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VENV_DIR="venv"

if [ ! -d "$VENV_DIR" ]; then
    echo "Virtual environment not found. Run ./setup.sh first."
    exit 1
fi

source "$VENV_DIR/bin/activate"

echo "Starting Travel Concierge Agent..."
echo "Open http://localhost:8501 in your browser"
echo ""

streamlit run app.py
