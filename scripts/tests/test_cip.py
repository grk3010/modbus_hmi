import asyncio
from modbus_client import ModbusClient

async def test():
    client = ModbusClient()
    print("Scanning...")
    # Use 255.255.255.255 as default broadcast for test
    devices = await client.scan_cip_network(timeout=3.0)
    print("Found devices:", devices)

if __name__ == "__main__":
    asyncio.run(test())
