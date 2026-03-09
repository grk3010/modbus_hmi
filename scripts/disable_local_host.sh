#!/bin/bash
# Stop and disable dnsmasq
systemctl stop dnsmasq
systemctl disable dnsmasq

# Dynamically find the connection for eth0
CONN_UUID=$(nmcli -t -f UUID,DEVICE connection show | grep ":eth0$" | cut -d: -f1)
if [ -z "$CONN_UUID" ]; then
    CONN_UUID=$(nmcli -t -f UUID,TYPE,DEVICE connection show | grep ":802-3-ethernet:.*$" | head -n1 | cut -d: -f1)
fi

if [ -n "$CONN_UUID" ]; then
    # Revert eth0 to automatic DHCP client
    nmcli connection modify "$CONN_UUID" ipv4.method auto ipv4.addresses "" ipv4.gateway ""
    
    # Restart the connection. We run this in the background because if there is no DHCP server 
    # on the eth0 link, this command will hang for ~45 seconds and then "fail".
    # By backgrounding it, the UI can return to the normal state immediately while NetworkManager 
    # does its thing.
    nohup nmcli connection up "$CONN_UUID" >/dev/null 2>&1 &
else
    echo "Warning: No connection found for eth0 to revert."
fi

exit 0
