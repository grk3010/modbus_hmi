#!/bin/bash

echo "Fixing Desktop Mode and Rotation..."

# 1. Backup the old raspi-config kiosk autostart if it exists
if [ -f /home/pi/.config/labwc/autostart ]; then
    echo "Found old labwc autostart. Backing it up to autostart.bak..."
    mv /home/pi/.config/labwc/autostart /home/pi/.config/labwc/autostart.bak
fi

# 2. Create a new autostart that rotates the screen and THEN loads the system desktop
mkdir -p /home/pi/.config/labwc
cat << 'EOF' > /home/pi/.config/labwc/autostart
#!/bin/bash
# Force screen rotation in the background (waits for labwc to be ready)
(sleep 1 && wlr-randr --output DSI-1 --transform 270) &

# Load the default Raspberry Pi desktop components (panel, background, etc)
if [ -f /etc/xdg/labwc/autostart ]; then
    . /etc/xdg/labwc/autostart
fi

# Launch the web interface in a normal window (so the user can close/minimize it)
(sleep 2 && chromium --incognito --noerrdialogs --disable-translate --no-first-run --fast --fast-start --disable-infobars --disable-features=TranslateUI --disk-cache-dir=/tmp/chromium_cache --password-store=basic --ozone-platform=wayland --enable-features=UseOzonePlatform http://localhost:8080) &
EOF
chmod +x /home/pi/.config/labwc/autostart

echo "Done! The 'Exit to Desktop' button should now correctly load the rotated PIXEL desktop."
