#!/bin/bash
# Stop and disable dnsmasq
systemctl stop dnsmasq
systemctl disable dnsmasq

# Revert eth0 to automatic DHCP client
nmcli connection modify "Wired connection 1" ipv4.method auto ipv4.addresses "" ipv4.gateway ""

# Restart the connection. We run this in the background because if there is no DHCP server 
# on the eth0 link, this command will hang for ~45 seconds and then "fail".
# By backgrounding it, the UI can return to the normal state immediately while NetworkManager 
# does its thing.
nohup nmcli connection up "Wired connection 1" >/dev/null 2>&1 &

exit 0
