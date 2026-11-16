#!/bin/bash
# ==============================================================================
# Configures Kiosk Mode, Desktop Mode Autostart, and Chromium Crash Prevention
# for Raspberry Pi OS (Debian Trixie / labwc) on reTerminal DM CM4
# ==============================================================================

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
USER_HOME="/home/pi"
LABWC_DIR="$USER_HOME/.config/labwc"

echo "Configuring Kiosk & Desktop Mode (labwc + Chromium)..."

mkdir -p "$LABWC_DIR"

# 1. Install system-wide Chromium pre-launch state cleaner (/etc/chromium.d/99-hmi-clean-state)
#    /usr/bin/chromium sources /etc/chromium.d/* on EVERY launch (including desktop icon clicks).
sudo mkdir -p /etc/chromium.d
sudo tee /etc/chromium.d/99-hmi-clean-state > /dev/null << 'EOF_CHROMIUM_D'
# Automatically sanitize Chromium crash flags before launch if no instance is currently running
if ! pgrep -u "$(id -u)" -f "/usr/lib/chromium/chromium" >/dev/null 2>&1; then
    for prof_dir in "$HOME/.config/chromium" "/tmp/chromium_kiosk" "/tmp/chromium_desktop"; do
        if [ -d "$prof_dir" ]; then
            rm -f "$prof_dir"/Singleton* 2>/dev/null || true
            rm -rf "$prof_dir/Default/Sessions" "$prof_dir/Sessions" 2>/dev/null || true
            if [ -f "$prof_dir/Default/Preferences" ]; then
                sed -i 's/"exit_type"[[:space:]]*:[[:space:]]*"[^"]*"/"exit_type":"Normal"/g' "$prof_dir/Default/Preferences" 2>/dev/null || true
                sed -i 's/"exited_cleanly"[[:space:]]*:[[:space:]]*false/"exited_cleanly":true/g' "$prof_dir/Default/Preferences" 2>/dev/null || true
            fi
            if [ -f "$prof_dir/Local State" ]; then
                sed -i 's/"exited_cleanly"[[:space:]]*:[[:space:]]*false/"exited_cleanly":true/g' "$prof_dir/Local State" 2>/dev/null || true
            fi
        fi
    done
fi
export CHROMIUM_FLAGS="$CHROMIUM_FLAGS --no-first-run --noerrdialogs --disable-infobars --check-for-update-interval=31536000"
EOF_CHROMIUM_D
sudo chmod 644 /etc/chromium.d/99-hmi-clean-state

# 2. Install Chromium Managed Policy to disable crash restore bubbles, welcome tabs, and password prompts
sudo mkdir -p /etc/chromium/policies/managed
sudo tee /etc/chromium/policies/managed/hmi_kiosk.json > /dev/null << 'EOF_POLICY'
{
  "PasswordManagerEnabled": false,
  "TranslateEnabled": false,
  "PromotionalTabsEnabled": false,
  "DefaultBrowserSettingEnabled": false,
  "BackgroundModeEnabled": false
}
EOF_POLICY
sudo chmod 644 /etc/chromium/policies/managed/hmi_kiosk.json

# 3. Create Kiosk Launch Script (~/.config/labwc/kiosk-launch.sh)
cat << 'EOF_KIOSK' > "$LABWC_DIR/kiosk-launch.sh"
#!/bin/bash
# Minimal Wayland Kiosk Launch (runs when booting into Kiosk mode)
exec > /tmp/kiosk.log 2>&1
echo "Kiosk started at $(date)"

# Force screen rotation to landscape (fixes rotation bug on warm restarts without Plymouth)
wlr-randr --output DSI-1 --transform 270 || true

# Start background splash while waiting for backend
pkill swaybg 2>/dev/null || true
swaybg -i /home/pi/modbus_hmi/iodd_files/assets/compressor_graphic.png -m fill &

# Wait for HMI server to accept connections
while ! curl -s http://localhost:8080 >/dev/null; do
    sleep 0.5
done

# Supervision loop: if Chromium ever crashes, clean profile and relaunch automatically
while true; do
    # Exit loop cleanly if labwc compositor is no longer running
    if [ -n "$LABWC_PID" ] && ! kill -0 "$LABWC_PID" 2>/dev/null; then
        break
    fi

    # Prepare a fresh, pre-seeded ephemeral profile in RAM (/tmp)
    rm -rf /tmp/chromium_kiosk
    mkdir -p /tmp/chromium_kiosk/Default
    touch "/tmp/chromium_kiosk/First Run"
    cat << 'EOF_PREFS' > /tmp/chromium_kiosk/Default/Preferences
{"browser":{"has_seen_welcome_page":true},"profile":{"exit_type":"Normal","exited_cleanly":true},"session":{"restore_on_startup":5}}
EOF_PREFS
    cat << 'EOF_STATE' > "/tmp/chromium_kiosk/Local State"
{"user_experience_metrics":{"stability":{"exited_cleanly":true}}}
EOF_STATE

    # Launch Chromium in Kiosk + App mode (--app bypasses SessionCrashedBubbleView completely)
    chromium \
        --user-data-dir=/tmp/chromium_kiosk \
        --disk-cache-dir=/tmp/chromium_cache \
        --kiosk \
        --app=http://localhost:8080 \
        --noerrdialogs \
        --no-first-run \
        --disable-translate \
        --disable-infobars \
        --disable-features=Translate,TranslateUI \
        --check-for-update-interval=31536000 \
        --password-store=basic \
        --ozone-platform=wayland \
        --enable-features=UseOzonePlatform

    EXIT_CODE=$?
    echo "Chromium kiosk exited with code $EXIT_CODE at $(date)"
    # If terminated cleanly by SIGTERM (143) or SIGINT (130) during shutdown/mode-switch, do not respawn
    if [ "$EXIT_CODE" -eq 0 ] || [ "$EXIT_CODE" -eq 143 ] || [ "$EXIT_CODE" -eq 130 ]; then
        break
    fi
    sleep 2
done
EOF_KIOSK
chmod +x "$LABWC_DIR/kiosk-launch.sh"

# 4. Create Desktop Autostart Script (~/.config/labwc/autostart)
#    IMPORTANT: labwc ALWAYS executes ~/.config/labwc/autostart even when `-s kiosk-launch.sh` is passed!
#    We guard the top of this script so it exits immediately when Kiosk mode is active.
cat << 'EOF_AUTOSTART' > "$LABWC_DIR/autostart"
#!/bin/bash
# Guard: If labwc was launched in Kiosk mode (-s kiosk-launch.sh), exit immediately
# so desktop panels and a duplicate browser window are NOT started alongside kiosk mode.
if tr '\0' ' ' < /proc/${LABWC_PID:-$PPID}/cmdline 2>/dev/null | grep -q "kiosk-launch"; then
    exit 0
fi

# Force screen rotation in the background (waits for labwc to be ready)
(sleep 1 && wlr-randr --output DSI-1 --transform 270) &

# Load the default Raspberry Pi desktop components (panel, background, file manager, etc.)
if [ -f /etc/xdg/labwc/autostart ]; then
    . /etc/xdg/labwc/autostart
fi

# Launch the web interface in a normal desktop window once localhost:8080 is ready
(
    while ! curl -s http://localhost:8080 >/dev/null; do
        sleep 0.5
    done
    rm -rf /tmp/chromium_desktop
    mkdir -p /tmp/chromium_desktop/Default
    touch "/tmp/chromium_desktop/First Run"
    cat << 'EOF_PREFS' > /tmp/chromium_desktop/Default/Preferences
{"browser":{"has_seen_welcome_page":true},"profile":{"exit_type":"Normal","exited_cleanly":true},"session":{"restore_on_startup":5}}
EOF_PREFS
    cat << 'EOF_STATE' > "/tmp/chromium_desktop/Local State"
{"user_experience_metrics":{"stability":{"exited_cleanly":true}}}
EOF_STATE

    chromium \
        --user-data-dir=/tmp/chromium_desktop \
        --disk-cache-dir=/tmp/chromium_cache \
        --noerrdialogs \
        --no-first-run \
        --disable-translate \
        --disable-infobars \
        --disable-features=Translate,TranslateUI \
        --check-for-update-interval=31536000 \
        --password-store=basic \
        --ozone-platform=wayland \
        --enable-features=UseOzonePlatform \
        http://localhost:8080
) &
EOF_AUTOSTART
chmod +x "$LABWC_DIR/autostart"

# 5. Create labwc shutdown hook (~/.config/labwc/shutdown) to close Chromium cleanly before Wayland exits
cat << 'EOF_SHUTDOWN' > "$LABWC_DIR/shutdown"
#!/bin/bash
pkill -TERM -f "/usr/lib/chromium/chromium" 2>/dev/null || true
EOF_SHUTDOWN
chmod +x "$LABWC_DIR/shutdown"

# Ensure ownership is pi:pi when invoked via sudo
chown -R pi:pi "$LABWC_DIR" 2>/dev/null || true

# Clean any existing crash state in default ~/.config/chromium right now
if [ -d "$USER_HOME/.config/chromium" ]; then
    rm -f "$USER_HOME/.config/chromium"/Singleton* 2>/dev/null || true
    rm -rf "$USER_HOME/.config/chromium/Default/Sessions" "$USER_HOME/.config/chromium/Sessions" 2>/dev/null || true
    if [ -f "$USER_HOME/.config/chromium/Default/Preferences" ]; then
        sed -i 's/"exit_type"[[:space:]]*:[[:space:]]*"[^"]*"/"exit_type":"Normal"/g' "$USER_HOME/.config/chromium/Default/Preferences" 2>/dev/null || true
        sed -i 's/"exited_cleanly"[[:space:]]*:[[:space:]]*false/"exited_cleanly":true/g' "$USER_HOME/.config/chromium/Default/Preferences" 2>/dev/null || true
    fi
    if [ -f "$USER_HOME/.config/chromium/Local State" ]; then
        sed -i 's/"exited_cleanly"[[:space:]]*:[[:space:]]*false/"exited_cleanly":true/g' "$USER_HOME/.config/chromium/Local State" 2>/dev/null || true
    fi
fi

echo "Done! Kiosk and Desktop launch configurations have been updated."
