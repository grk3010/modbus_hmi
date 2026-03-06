#!/bin/bash
# enable_local_host.sh
# Usage: ./enable_local_host.sh <ip_address>
# Example: ./enable_local_host.sh 172.16.1.1

IP_ADDR=${1:-172.16.1.1}

# Extract the first 3 octets to form the subnet prefix
PREFIX=$(echo "$IP_ADDR" | cut -d. -f1-3)

echo "Configuring eth0 static IP: $IP_ADDR"
# Set static IP on eth0 for IO-Link Master network
nmcli connection modify "Wired connection 1" ipv4.method manual ipv4.addresses "$IP_ADDR/24" ipv4.gateway ""
nmcli connection up "Wired connection 1"

echo "Configuring dnsmasq with DHCP range: $PREFIX.100 - $PREFIX.200"
# Configure dnsmasq to serve the provided subnet
cat <<EOF > /etc/dnsmasq.conf
interface=eth0
bind-interfaces
dhcp-range=$PREFIX.100,$PREFIX.200,255.255.255.0,24h
EOF

# Restart and enable dnsmasq
systemctl restart dnsmasq
systemctl enable dnsmasq
