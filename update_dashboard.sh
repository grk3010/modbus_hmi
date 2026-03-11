#!/bin/bash

# ==============================================================================
# Modbus HMI - Update Script
# ==============================================================================
# Updates the dashboard from Git (online) or a local tarball (offline).
#
# Usage:
#   Online:  ./update_dashboard.sh
#   Offline: ./update_dashboard.sh /path/to/modbus_hmi_update.tar.gz
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

# Detect virtual environment
if [ -d "venv" ]; then
  VENV_DIR="venv"
elif [ -d ".venv" ]; then
  VENV_DIR=".venv"
else
  echo "Error: No virtual environment found."
  exit 1
fi

CURRENT_VERSION=$(cat VERSION 2>/dev/null || echo "unknown")
echo "========================================="
echo " Modbus HMI Updater"
echo " Current Version: $CURRENT_VERSION"
echo "========================================="

if [ -n "$1" ]; then
  # --- Offline Update from Tarball ---
  TARBALL="$1"
  if [ ! -f "$TARBALL" ]; then
    echo "Error: File not found: $TARBALL"
    exit 1
  fi

  echo "Applying offline update from: $TARBALL"

  # Create a backup
  BACKUP_DIR="/tmp/modbus_hmi_backup_$(date +%Y%m%d_%H%M%S)"
  echo "Creating backup at: $BACKUP_DIR"
  cp -r "$SCRIPT_DIR" "$BACKUP_DIR"

  # Extract update (overwrite existing files)
  tar -xzf "$TARBALL" -C "$SCRIPT_DIR" --strip-components=1
  EXTRACT_STATUS=$?

  if [ $EXTRACT_STATUS -ne 0 ]; then
    echo "Error: Failed to extract tarball. Restoring backup..."
    cp -r "$BACKUP_DIR/"* "$SCRIPT_DIR/"
    exit 1
  fi

  echo "Files updated successfully."
else
  # --- Online Update via Git ---
  if ! command -v git &> /dev/null; then
    echo "Error: git is not installed."
    exit 1
  fi

  if [ ! -d ".git" ]; then
    echo "Error: Not a git repository. Use offline update instead."
    exit 1
  fi

  echo "Fetching latest changes from remote..."
  git fetch --all 2>&1

  LOCAL=$(git rev-parse HEAD)
  REMOTE=$(git rev-parse @{u} 2>/dev/null)

  if [ "$LOCAL" = "$REMOTE" ]; then
    echo "Already up to date."
    exit 0
  fi

  echo "Pulling latest changes..."
  git pull --ff-only 2>&1
  PULL_STATUS=$?

  if [ $PULL_STATUS -ne 0 ]; then
    echo "Error: git pull failed. You may have local changes."
    echo "Try: git stash && git pull && git stash pop"
    exit 1
  fi
fi

# --- Post-Update Steps ---
echo "Installing/updating dependencies..."
"./$VENV_DIR/bin/pip" install -r requirements.txt --quiet 2>&1

NEW_VERSION=$(cat VERSION 2>/dev/null || echo "unknown")
echo "========================================="
echo " Update Complete!"
echo " Version: $CURRENT_VERSION -> $NEW_VERSION"
echo "========================================="

# Restart service if running under systemd
if systemctl is-active --quiet modbus_hmi 2>/dev/null; then
  echo "Restarting modbus_hmi service..."
  sudo systemctl restart modbus_hmi
  echo "Service restarted."
fi
