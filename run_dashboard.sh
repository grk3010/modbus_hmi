#!/bin/bash

# ==============================================================================
# Modbus HMI - Run Dashboard (Development / Non-Kiosk)
# ==============================================================================
# Activates the Python virtual environment and starts the HMI dashboard.
# No kiosk mode, no systemd — just runs in the foreground.
#
# Usage: ./run_dashboard.sh [--port PORT]
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

# Default port
PORT=8080

# Parse arguments
for arg in "$@"; do
  case $arg in
    --port)
      shift
      PORT="$1"
      shift
      ;;
    --port=*)
      PORT="${arg#*=}"
      ;;
  esac
done

# Detect virtual environment
if [ -d "venv" ]; then
  VENV_DIR="venv"
elif [ -d ".venv" ]; then
  VENV_DIR=".venv"
else
  echo "Error: No virtual environment found (venv/ or .venv/)."
  echo "Create one with: python3 -m venv venv && ./venv/bin/pip install -r requirements.txt"
  exit 1
fi

echo "========================================="
echo " Modbus HMI Dashboard"
echo " Virtual Env: $VENV_DIR"
echo " Port:        $PORT"
echo " URL:         http://localhost:$PORT"
echo "========================================="

# Activate and run
source "$VENV_DIR/bin/activate"
exec python main.py
