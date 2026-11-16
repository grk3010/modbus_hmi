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

# Check if resuming from automated Stage 2 reboot sequence
IS_STAGE2_RESUME=false
if [ "$1" = "--stage2-resume" ]; then
  IS_STAGE2_RESUME=true
  shift
fi

# Detect active OverlayFS configuration
OVERLAY_ACTIVE=false
if grep -q "overlay / " /proc/mounts 2>/dev/null || grep -q "overlayroot" /proc/mounts 2>/dev/null; then
  OVERLAY_ACTIVE=true
fi

if [ "$OVERLAY_ACTIVE" = true ] && [ "$IS_STAGE2_RESUME" = false ]; then
  echo "=================================================="
  echo " OverlayFS is currently ACTIVE (Read-Only Root)   "
  echo " Staging automated two-stage update sequence...   "
  echo "=================================================="
  
  MARKER_DIR="/mnt/ssd"
  if [ ! -d "/mnt/ssd" ]; then
    MARKER_DIR="/boot/firmware"
  fi
  MARKER_FILE="${MARKER_DIR}/.update_pending"
  
  echo "Dropping persistent update flag at $MARKER_FILE..."
  sudo touch "$MARKER_FILE"
  sudo chmod 777 "$MARKER_FILE" || true
  
  if [ -n "$1" ]; then
    if [ ! -f "$1" ]; then
      echo "Error: Update tarball not found: $1"
      sudo rm -f "$MARKER_FILE"
      exit 1
    fi
    # Copy tarball to persistent storage so it survives the Stage 1 reboot (since /tmp is tmpfs)
    STAGED_TARBALL="${MARKER_DIR}/.staged_update.tar.gz"
    echo "Persisting offline update archive to $STAGED_TARBALL..."
    sudo cp "$1" "$STAGED_TARBALL"
    sudo chmod 666 "$STAGED_TARBALL" || true
    echo "$STAGED_TARBALL" | sudo tee "${MARKER_FILE}_target" > /dev/null
    sudo chmod 777 "${MARKER_FILE}_target" || true
  fi
  
  echo "Disabling OverlayFS to temporarily unlock base storage..."
  sudo raspi-config nonint disable_overlayfs
  
  echo "Rebooting into writeable staging state..."
  nohup sudo bash -c "sleep 2 && reboot" >/dev/null 2>&1 &
  exit 0
fi

if [ -n "$1" ]; then
  # --- Offline Update from Tarball ---
  TARBALL="$1"
  if [ ! -f "$TARBALL" ]; then
    echo "Error: File not found: $TARBALL"
    exit 1
  fi

  echo "Applying offline update from: $TARBALL"

  # Create a lightweight backup of application code (excluding venv, .git, and large SQLite DBs)
  BACKUP_DIR="/tmp/modbus_hmi_backup_$(date +%Y%m%d_%H%M%S)"
  echo "Creating code backup at: $BACKUP_DIR"
  mkdir -p "$BACKUP_DIR"
  tar --exclude='./venv' \
      --exclude='./.venv' \
      --exclude='./.git' \
      --exclude='./__pycache__' \
      --exclude='./*.db*' \
      -cf - -C "$SCRIPT_DIR" . | tar -xf - -C "$BACKUP_DIR"

  # Detect whether tarball has a top-level wrapper directory or flat root files
  STRIP_ARGS=""
  if ! tar -tzf "$TARBALL" 2>/dev/null | grep -qE '^(\./)?main\.py$'; then
    if tar -tzf "$TARBALL" 2>/dev/null | grep -qE '^[^/]+/main\.py$'; then
      STRIP_ARGS="--strip-components=1"
    fi
  fi

  # Extract update (overwrite existing files)
  tar -xzf "$TARBALL" -C "$SCRIPT_DIR" $STRIP_ARGS
  EXTRACT_STATUS=$?

  if [ $EXTRACT_STATUS -ne 0 ]; then
    echo "Error: Failed to extract tarball. Restoring backup..."
    cp -r "$BACKUP_DIR/"* "$SCRIPT_DIR/"
    exit 1
  fi

  # Remove temporary/staged tarball after successful extraction
  if [[ "$TARBALL" == /tmp/* ]] || [[ "$TARBALL" == */.staged_update.tar.gz ]]; then
    sudo rm -f "$TARBALL" 2>/dev/null || true
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

  echo "Overwriting local changes and syncing with remote repository..."
  git reset --hard @{u} 2>&1
  git clean -fd 2>&1
  PULL_STATUS=$?

  if [ $PULL_STATUS -ne 0 ]; then
    echo "Error: Failed to sync with remote tracking branch."
    exit 1
  fi
fi

# --- Post-Update Steps ---
echo "Installing/updating dependencies..."
"./$VENV_DIR/bin/pip" install -r requirements.txt --quiet 2>&1

# Update Kiosk & Desktop launch scripts and Chromium crash prevention policies
if [ -f "fix_desktop.sh" ]; then
  echo "Updating Kiosk & Desktop launch configurations..."
  bash ./fix_desktop.sh
fi

# Update auxiliary systemd services if installed
if [ -f "/etc/systemd/system/ups_shutdown.service" ]; then
  echo "Updating ups_shutdown.service..."
  sudo cp scripts/ups_shutdown.service /etc/systemd/system/
fi

if [ -f "/etc/systemd/system/modbus_updater_staging.service" ]; then
  echo "Updating modbus_updater_staging.service..."
  sudo cp scripts/modbus_updater_staging.service /etc/systemd/system/
fi

echo "Reloading systemd daemon..."
sudo systemctl daemon-reload || true

if systemctl is-active --quiet ups_shutdown.service 2>/dev/null; then
  echo "Restarting ups_shutdown.service..."
  sudo systemctl restart ups_shutdown.service
fi

NEW_VERSION=$(cat VERSION 2>/dev/null || echo "unknown")
echo "========================================="
echo " Update Complete!"
echo " Version: $CURRENT_VERSION -> $NEW_VERSION"
echo "========================================="

# Restart service if running under systemd
if systemctl is-active --quiet modbus_hmi 2>/dev/null; then
  if [ "$IS_STAGE2_RESUME" = true ]; then
    echo "Restarting modbus_hmi service..."
    sudo systemctl restart modbus_hmi
    echo "Service restarted."
  else
    echo "Scheduling modbus_hmi service restart in 2 seconds..."
    nohup sudo bash -c "sleep 2 && systemctl restart modbus_hmi" >/dev/null 2>&1 &
  fi
fi

