#!/bin/bash
# Final Installation Script for CLI-first Kiosk Boot
# Targets: Raspberry Pi OS (Trixie) on reTerminal CM4

PROJECT_DIR="/home/pi/modbus_hmi"
ACTUAL_USER="pi"
USER_HOME="/home/pi"

echo "Configuring CLI-first Kiosk Boot..."

# 1. Set System to Boot to CLI with Autologin
sudo raspi-config nonint do_boot_behaviour B2

# 2. Install Dependencies
sudo apt-get update
sudo apt-get install -y swaybg curl chromium

# 3. Setup Project Assets
sudo cp "$PROJECT_DIR/iodd_files/assets/compressor_graphic.png" /usr/share/plymouth/themes/pix/splash.png

# 4. Create Minimal Kiosk Launch Script
KIOSK_SCRIPT="$USER_HOME/.config/labwc/kiosk-launch.sh"
sudo -u "$ACTUAL_USER" mkdir -p "$(dirname "$KIOSK_SCRIPT")"
sudo -u "$ACTUAL_USER" cat << 'EOF_KIOSK' > "$KIOSK_SCRIPT"
#!/bin/bash
# Minimal Wayland Kiosk Launch
exec > /tmp/kiosk.log 2>&1
echo "Kiosk started at $(date)"

# Force screen rotation to landscape (fixes rotation bug on warm restarts without Plymouth)
wlr-randr --output DSI-1 --transform 270 || true

swaybg -i /home/pi/modbus_hmi/iodd_files/assets/compressor_graphic.png -m fill &

# Wait for HMI server
while ! curl -s http://localhost:8080 >/dev/null; do sleep 1; done

# Clean state
rm -rf /home/pi/.config/chromium/Singleton*

# Launch Chromium
chromium --kiosk --incognito --noerrdialogs --disable-translate --no-first-run --fast --fast-start --disable-infobars --disable-features=TranslateUI --disk-cache-dir=/tmp/chromium_cache --password-store=basic --ozone-platform=wayland --enable-features=UseOzonePlatform http://localhost:8080
EOF_KIOSK
chmod +x "$KIOSK_SCRIPT"

# 5. Update .profile for Login Launch
PROFILE="$USER_HOME/.profile"
if ! grep -q "kiosk-launch.sh" "$PROFILE"; then
  cat << 'EOF_PROFILE' >> "$PROFILE"

# Wayland / Kiosk Launch for CLI-first boot
if [ -z "$XDG_RUNTIME_DIR" ]; then
    export XDG_RUNTIME_DIR=/run/user/$(id -u)
fi
if [ -z "$DISPLAY" ] && [ "$(tty)" = "/dev/tty1" ]; then
    if [ ! -f "$HOME/.no_kiosk" ]; then
        exec labwc -s /home/pi/.config/labwc/kiosk-launch.sh
    else
        rm "$HOME/.no_kiosk"
        exec labwc
    fi
fi
EOF_PROFILE
fi

# 6. Ensure HMI Service is Enabled
sudo systemctl enable modbus_hmi.service
sudo systemctl restart modbus_hmi.service

# 7. Setup UPS Shutdown Service
sudo cp "$PROJECT_DIR/scripts/ups_shutdown.service" /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable ups_shutdown.service
sudo systemctl restart ups_shutdown.service

# 8. Configure Hardware Watchdog
echo "Configuring Hardware Watchdog..."
sudo apt-get install -y watchdog
if ! grep -q "dtparam=watchdog=on" /boot/firmware/config.txt; then
    echo "dtparam=watchdog=on" | sudo tee -a /boot/firmware/config.txt
fi
sudo sed -i 's/#watchdog-device/watchdog-device/g' /etc/watchdog.conf
sudo sed -i 's/#watchdog-timeout/watchdog-timeout/g' /etc/watchdog.conf
if ! grep -q "watchdog-timeout = 15" /etc/watchdog.conf; then
    sudo sed -i 's/watchdog-timeout.*/watchdog-timeout = 15/g' /etc/watchdog.conf
fi
sudo systemctl enable watchdog
sudo systemctl start watchdog

# 9. Setup Automated Update Staging Service
echo "Configuring Automated OverlayFS Update Staging Service..."
sudo cp "$PROJECT_DIR/scripts/modbus_updater_staging.service" /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable modbus_updater_staging.service

echo "Configuration complete. Please REBOOT."
