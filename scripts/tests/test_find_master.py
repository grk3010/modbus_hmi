import asyncio
from modbus_client import ModbusClient

async def scan():
    client = ModbusClient()
    print("Scanning for Keyence Masters...")
    # Try common broadcast addresses or local subnets
    devices = await client.scan_cip_network(broadcast_ip="255.255.255.255", timeout=3.0)
    if not devices:
        # Try local subnets if broadcast fails
        print("No devices found via broadast. Checking local interfaces...")
        # (This is a simplified version of what's in config_page)
        import subprocess
        try:
            output = subprocess.check_output("ip -o addr show", shell=True).decode()
            for line in output.split("\n"):
                if "inet " in line and "/24" in line:
                    subnet = line.split()[3]
                    import ipaddress
                    net = ipaddress.IPv4Network(subnet, strict=False)
                    print(f"Scanning subnet {net}...")
                    devices.extend(await client.scan_cip_network(broadcast_ip=str(net.broadcast_address), timeout=2.0))
        except:
            pass
            
    if devices:
        for dev in devices:
            print(f"Found: {dev['product_name']} at {dev['ip']}")
    else:
        print("No devices found.")

if __name__ == "__main__":
    asyncio.run(scan())
