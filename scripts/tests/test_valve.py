import asyncio
from pymodbus.client import AsyncModbusTcpClient
from modbus_client import ModbusClient

async def test_valve(ip, port_num, state):
    client = ModbusClient()
    client.host = ip
    await client.connect()
    
    if client.connected:
        print(f"Connected to {ip}")
        success = await client.write_valve(port_num, state)
        print(f"Write valve to port {port_num} state {state}: {'SUCCESS' if success else 'FAILED'}")
        
        # Read back address 2048 to see what bits are set
        resp = await client.client.read_holding_registers(address=2048, count=1)
        if not resp.isError():
            print(f"Address 2048 is now: {bin(resp.registers[0])}")
        else:
            print("Failed to read back address 2048")
    else:
        print(f"Failed to connect to {ip}")

if __name__ == "__main__":
    ip = "172.16.1.90"
    
    # Toggle Port 1 ON
    import sys
    state = True
    if len(sys.argv) > 1:
        state = sys.argv[1].lower() == 'true'
        
    asyncio.run(test_valve(ip, 1, state))
