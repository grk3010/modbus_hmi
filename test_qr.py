from nicegui import ui

@ui.page('/')
def main():
    def get_network_interfaces():
        import subprocess
        interfaces = []
        try:
            output = subprocess.check_output("ip -o addr show", shell=True).decode()
            for line in output.split("\n"):
                if not line: continue
                parts = line.split()
                if len(parts) >= 4 and parts[2] == "inet":
                    interfaces.append({"iface": parts[1], "ip": parts[3]})
        except Exception:
            pass
        if not interfaces:
            interfaces.append({"iface": "localhost", "ip": "127.0.0.1/8"})
        return interfaces

    ui.label("Remote Access").classes('text-h6')
    
    interfaces = get_network_interfaces()
    
    wlan_iface = next((i for i in interfaces if "wlan" in i["iface"]), None)
    default_ip = "127.0.0.1"
    
    if wlan_iface:
        default_ip = wlan_iface["ip"].split("/")[0]
    else:
        for iface in interfaces:
            if iface["ip"].startswith("127."):
                continue
            default_ip = iface["ip"].split("/")[0]
            break

    # Deduplicate by interface name and ip
    ip_options = {}
    for iface in interfaces:
        ip_addr = iface["ip"].split("/")[0]
        ip_options[ip_addr] = f'{iface["iface"]} ({ip_addr})'
        
    remote_ip = ui.select(ip_options, value=default_ip, label="Select Network Interface").classes('w-full')

    @ui.refreshable
    def render_qr():
        current_ip = remote_ip.value
        ui.html(f'<img src="https://api.qrserver.com/v1/create-qr-code/?size=150x150&data=http://{current_ip}:8080" />')
        ui.label(f"http://{current_ip}:8080").classes('text-subtitle1 text-grey font-mono q-mt-sm')

    remote_ip.on('update:model-value', render_qr.refresh)
    # Render initially
    render_qr()

ui.run(port=8084, show=False)
