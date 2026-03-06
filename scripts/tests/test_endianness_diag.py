import asyncio
import struct
from pymodbus.client import AsyncModbusTcpClient
import json

async def diagnostic():
    # Load current settings to get IP and port mappings
    try:
        with open("hmi_settings.json", "r") as f:
            settings = json.load(f)
    except:
        print("Could not load hmi_settings.json")
        return

    ip = settings.get("master_ip", "127.0.0.1")
    print(f"Connecting to Modbus Master at {ip}...")
    
    client = AsyncModbusTcpClient(ip, port=502)
    connected = await client.connect()
    if not connected:
        print("Failed to connect.")
        return

    print("--- RAW REGISTER DIAGNOSTIC ---")
    for port in range(1, 4): # Check first 3 ports
        addr = settings.get(f"{port}_modbus_address")
        count = settings.get(f"{port}_modbus_length", 16)
        
        if addr is None: continue
        
        print(f"\nPORT {port} (Address: {addr}, Count: {count}):")
        resp = await client.read_holding_registers(address=int(addr), count=int(count))
        if resp.isError():
            print(f"  Error reading registers: {resp}")
        else:
            regs = resp.registers
            print(f"  Registers (Hex): {[hex(r) for r in regs[:8]]} ...")
            
            # Show Byte Swap Version
            swapped = []
            for r in regs:
                # 0x1234 -> 0x3412
                s = ((r << 8) & 0xFF00) | ((r >> 8) & 0x00FF)
                swapped.append(s)
            print(f"  Swapped (Hex):   {[hex(s) for s in swapped[:8]]} ...")

    client.close()

if __name__ == "__main__":
    asyncio.run(diagnostic())
