import asyncio
from pymodbus.client import AsyncModbusTcpClient

async def sync_scan():
    c = AsyncModbusTcpClient('172.16.1.90', port=502)
    await c.connect()
    valid_blocks = []
    
    # Process data usually around 1000H (4096) or 0
    # Let's test a few specific addresses: 4000, 4096, 4097, 1000H..
    test_addrs = [4096, 4097, 8192, 0, 1000, 2000, 3000, 4000]
    
    for a in test_addrs:
        r = await c.read_holding_registers(address=a, count=10)
        if not r.isError():
            print(f"Holding found at {a}: {r.registers}")
            
        r2 = await c.read_input_registers(address=a, count=10)
        if not r2.isError():
            print(f"Input found at {a}: {r2.registers}")
            
    await c.close()

asyncio.run(sync_scan())
