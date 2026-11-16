#!/bin/bash
# Autonomous Boot Execution Script for Automated Two-Stage OverlayFS Updates
# Resumes update_dashboard.sh on writeable base filesystem, re-enables overlay, and reboots

MARKER_SSD="/mnt/ssd/.update_pending"
MARKER_BOOT="/boot/firmware/.update_pending"

TARGET_MARKER=""
if [ -f "$MARKER_SSD" ]; then
    TARGET_MARKER="$MARKER_SSD"
elif [ -f "$MARKER_BOOT" ]; then
    TARGET_MARKER="$MARKER_BOOT"
fi

if [ -n "$TARGET_MARKER" ]; then
    LOG_FILE="/mnt/ssd/update_staging.log"
    if [ ! -d "/mnt/ssd" ]; then 
        LOG_FILE="/tmp/update_staging.log"
    fi
    
    echo "==================================================" >> "$LOG_FILE"
    echo " Resuming Automated OverlayFS Update at $(date)   " >> "$LOG_FILE"
    echo " Marker Flag found at: $TARGET_MARKER             " >> "$LOG_FILE"
    echo "==================================================" >> "$LOG_FILE"

    TARBALL_ARG=""
    if [ -f "${TARGET_MARKER}_target" ]; then
        TARBALL_ARG=$(cat "${TARGET_MARKER}_target" 2>/dev/null)
        rm -f "${TARGET_MARKER}_target"
    fi
    
    # Remove marker to ensure zero boot loop risk
    rm -f "$TARGET_MARKER"
    
    cd /home/pi/modbus_hmi || exit 1

    # If performing an online git update on boot, wait up to 30s for network routing/DNS
    if [ -z "$TARBALL_ARG" ]; then
        echo "Waiting for network connectivity before fetching git updates..." >> "$LOG_FILE"
        for _ in $(seq 1 30); do
            if git ls-remote origin HEAD >/dev/null 2>&1 || ping -c 1 -W 1 8.8.8.8 >/dev/null 2>&1; then
                break
            fi
            sleep 1
        done
    fi
    
    echo "Executing update_dashboard.sh --stage2-resume..." >> "$LOG_FILE"
    # Run as user pi (or restore ownership after) so .git and venv are never locked to root
    sudo -u pi /bin/bash ./update_dashboard.sh --stage2-resume $TARBALL_ARG >> "$LOG_FILE" 2>&1
    chown -R pi:pi /home/pi/modbus_hmi 2>/dev/null || true
    
    echo "Updates and dependencies successfully applied." >> "$LOG_FILE"
    echo "Re-enabling OverlayFS read-only root security..." >> "$LOG_FILE"
    sudo raspi-config nonint enable_overlayfs
    
    echo "Waiting 5 seconds to securely flush kernel and disk I/O buffers..." >> "$LOG_FILE"
    sleep 5
    
    echo "Triggering final relocking reboot sequence..." >> "$LOG_FILE"
    sudo reboot
    exit 0
fi
