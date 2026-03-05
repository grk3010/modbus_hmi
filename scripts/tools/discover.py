import asyncio
from pymodbus.client import AsyncModbusTcpClient

async def scan():
    c = AsyncModbusTcpClient("172.16.1.90")
    await c.connect()
    if not c.connected:
        print("cannot connect")
        return
        
    for addr in [0, 100, 200, 500, 1000, 2000, 3000, 4000, 5000, 6000, 7000, 8000]:
        r = await c.read_holding_registers(addr, 20)
        if hasattr(r, 'registers'):
            b = b"".join(x.to_bytes(2, "big") for x in r.registers)
            text = "".join(chr(c) if 32 <= c < 127 else "." for c in b)
            if any(c != "." for c in text):
                print(f"{addr}: {text}")
                
    await c.close()
    
asyncio.run(scan())
