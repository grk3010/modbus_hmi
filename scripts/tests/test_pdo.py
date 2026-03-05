import asyncio
from pymodbus.client import AsyncModbusTcpClient
from modbus_client import ModbusClient

async def test_pdo(ip, port_num, state):
    client = ModbusClient()
    client.host = ip
    await client.connect()
    
    if client.connected:
        print(f"Connected to {ip}")
        # Base Output Process Data address starts at 2049 for Port 1
        # Port 1 = 2049, Port 2 = 2065, Port 3 = 2081...
        addr = 2049 + ((port_num - 1) * 16)
        
        # According to IODD:
        # Bit 0 = Valve Open
        # Bit 1 = Valve Close
        
        # We write 1 for Open, 2 for Close (Bit 1 High)
        # Note: Modbus registers are 16-bit. The PDOut is an 8-bit record.
        # It's usually mapped to the lower byte of the 16-bit register (or higher depending on endianness).
        # We'll just write the integer value 1 or 2 to the register.
        val = 1 if state else 2
        
        print(f"Writing {val} to Modbus Address {addr}")
        resp = await client.client.write_register(addr, val)
        if not resp.isError():
            print("SUCCESS")
            
            # Read back
            rb = await client.client.read_holding_registers(address=addr, count=1)
            if not rb.isError():
                print(f"Read back address {addr}: {bin(rb.registers[0])}")
        else:
            print("FAILED")
    else:
        print(f"Failed to connect to {ip}")

if __name__ == "__main__":
    ip = "172.16.1.90"
    import sys
    state = True
    if len(sys.argv) > 1:
        state = sys.argv[1].lower() == 'true'
        
    asyncio.run(test_pdo(ip, 1, state))
