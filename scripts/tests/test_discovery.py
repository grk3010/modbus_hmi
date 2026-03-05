import asyncio
from modbus_client import ModbusClient

async def test_discovery():
    client = ModbusClient()
    ip = "172.16.1.90"
    print(f"Testing discovery on {ip}...")
    sensors = await client.discover_connected_sensors(ip, num_ports=8)
    print("Discovered sensors dictionary:", sensors)
    
if __name__ == "__main__":
    asyncio.run(test_discovery())
