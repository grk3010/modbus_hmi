#!/bin/bash
# enable_local_host.sh
# Usage: ./enable_local_host.sh <ip_address>
# Example: ./enable_local_host.sh 172.16.1.1

IP_ADDR=${1:-172.16.1.1}

# Extract the first 3 octets to form the subnet prefix
PREFIX=$(echo "$IP_ADDR" | cut -d. -f1-3)

# Dynamically find the connection for eth0
CONN_UUID=$(nmcli -t -f UUID,DEVICE connection show | grep ":eth0$" | cut -d: -f1)
if [ -z "$CONN_UUID" ]; then
    CONN_UUID=$(nmcli -t -f UUID,TYPE,DEVICE connection show | grep ":802-3-ethernet:.*$" | head -n1 | cut -d: -f1)
fi
if [ -z "$CONN_UUID" ]; then
    nmcli connection add type ethernet ifname eth0 con-name eth0_local
    CONN_UUID=$(nmcli -t -f UUID,DEVICE connection show | grep ":eth0$" | head -n1 | cut -d: -f1)
fi

echo "Configuring eth0 static IP: $IP_ADDR via connection $CONN_UUID"
# Set static IP on eth0 for IO-Link Master network
nmcli connection modify "$CONN_UUID" ipv4.method manual ipv4.addresses "$IP_ADDR/24" ipv4.gateway ""
nmcli connection up "$CONN_UUID"

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
