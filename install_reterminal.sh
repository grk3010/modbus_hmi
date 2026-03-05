#!/bin/bash

# ==============================================================================
# Modbus HMI - reTerminal Deployment Script
# ==============================================================================
# This script installs dependencies, creates a systemd service, and configures
# the LXDE-pi autostart file to boot the reTerminal directly into Kiosk mode.
# Run this script with sudo: sudo ./install_reterminal.sh
# ==============================================================================

if [ "$EUID" -ne 0 ]; then
  echo "Please run this script as root (sudo ./install_reterminal.sh)"
  exit 1
fi

USER_HOME="/home/pi"
APP_DIR="$USER_HOME/modbus_hmi"

echo "========================================="
echo " Starting Modbus HMI Deployment"
echo "========================================="

echo "[1/4] Installing system dependencies..."
apt-get update
apt-get install -y python3-venv python3-pip

echo "[2/4] Setting up Python virtual environment..."
cd "$APP_DIR" || { echo "App directory not found at $APP_DIR. Exiting."; exit 1; }

sudo -u pi python3 -m venv venv
sudo -u pi ./venv/bin/pip install -r requirements.txt

echo "[3/4] Configuring systemd auto-start service..."
SERVICE_FILE="/etc/systemd/system/modbus_hmi.service"
cat <<EOF > "$SERVICE_FILE"
[Unit]
Description=Keyence/Atlas Copco Modbus HMI Server
After=network.target

[Service]
User=pi
WorkingDirectory=$APP_DIR
Environment="PATH=$APP_DIR/venv/bin"
ExecStart=$APP_DIR/venv/bin/python main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable modbus_hmi.service
systemctl restart modbus_hmi.service

echo "[4/4] Configuring Kiosk Mode (Chromium)..."
AUTOSTART_FILE="/etc/xdg/lxsession/LXDE-pi/autostart"

if [ -f "$AUTOSTART_FILE" ]; then
  # Disable screensaver and power management
  if ! grep -q "@xset s noblank" "$AUTOSTART_FILE"; then echo "@xset s noblank" >> "$AUTOSTART_FILE"; fi
  if ! grep -q "@xset s off" "$AUTOSTART_FILE"; then echo "@xset s off" >> "$AUTOSTART_FILE"; fi
  if ! grep -q "@xset -dpms" "$AUTOSTART_FILE"; then echo "@xset -dpms" >> "$AUTOSTART_FILE"; fi
  
  # Comment out xscreensaver if it exists
  sed -i 's/@xscreensaver -no-splash/#@xscreensaver -no-splash/g' "$AUTOSTART_FILE"

  # Add Chromium kiosk command if not present
  if ! grep -q "chromium-browser --kiosk" "$AUTOSTART_FILE"; then
    echo "@chromium-browser --kiosk --incognito --noerrdialogs --disable-translate --no-first-run --fast --fast-start --disable-infobars --disable-features=TranslateUI --disk-cache-dir=/dev/null http://localhost:8080" >> "$AUTOSTART_FILE"
  fi
  echo "Kiosk mode configured successfully."
else
  echo "LXDE-pi autostart file not found. If this uses Wayland/Wayfire, manual configuration is required."
fi

echo "========================================="
echo " Deployment Complete!"
echo " The HMI server is now running in the background."
echo " A reboot is recommended to verify Kiosk mode: sudo reboot"
echo "========================================="
