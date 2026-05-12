#!/bin/bash
# M.2 SSD Interactive Setup Script for reTerminal DM
# Scans available NVMe drives, formats as ext4, and configures /etc/fstab

set -e

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root (use sudo)"
  exit 1
fi

echo "==========================================="
echo "   M.2 SSD Setup & Formatting Utility      "
echo "==========================================="
echo ""

echo "Scanning for available NVMe block devices..."
lsblk -d -o NAME,SIZE,MODEL,TYPE | grep disk || true
echo ""

dev_name="$1"
force_mode="$2"

if [ -z "$dev_name" ]; then
    read -p "Enter the device name to format (e.g., nvme0n1): " dev_name
fi

if [ -z "$dev_name" ]; then
    echo "No device specified. Exiting."
    exit 1
fi

target_disk="/dev/$dev_name"
target_part="${target_disk}p1"

if [ ! -b "$target_disk" ]; then
    echo "Error: Block device $target_disk not found!"
    exit 1
fi

if [ "$force_mode" != "--force" ]; then
    echo ""
    echo "WARNING: All data on $target_disk will be PERMANENTLY DESTROYED!"
    read -p "Are you absolutely sure you want to proceed? (type 'yes' to confirm): " confirm

    if [ "$confirm" != "yes" ]; then
        echo "Operation cancelled."
        exit 0
    fi
else
    echo "Force mode enabled. Proceeding without interactive confirmation."
fi

echo "Creating GPT partition table on $target_disk..."
# Use scriptable fdisk to create a single primary partition covering the disk
printf "g\nn\n1\n\n\nw\n" | fdisk "$target_disk" > /dev/null 2>&1 || true

# Give the kernel a moment to register the new partition
sleep 2

if [ ! -b "$target_part" ]; then
    echo "Partition $target_part not found. Attempting direct device formatting if partition creation differed..."
    target_part="$target_disk"
fi

echo "Formatting $target_part as ext4..."
mkfs.ext4 -F "$target_part"

mount_point="/mnt/ssd"
echo "Creating mount directory at $mount_point..."
mkdir -p "$mount_point"

echo "Retrieving UUID for $target_part..."
uuid=$(blkid -s UUID -o value "$target_part")

if [ -z "$uuid" ]; then
    echo "Error retrieving UUID. Setup incomplete."
    exit 1
fi

echo "UUID found: $uuid"

# Check if already in fstab
if grep -q "$uuid" /etc/fstab; then
    echo "Drive already configured in /etc/fstab."
else
    echo "Backing up /etc/fstab..."
    cp /etc/fstab /etc/fstab.bak
    echo "Adding drive entry to /etc/fstab..."
    echo "UUID=$uuid $mount_point ext4 defaults,noatime 0 2" >> /etc/fstab
fi

echo "Mounting $mount_point..."
mount -a

echo "Setting generous ownership permissions for non-root users..."
chmod 777 "$mount_point" || true

echo ""
echo "==========================================="
echo " SUCCESS: M.2 SSD mounted to $mount_point  "
echo "==========================================="
echo "Verify status using 'df -h $mount_point'"
