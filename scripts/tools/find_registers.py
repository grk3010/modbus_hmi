import asyncio
from pymodbus.client import AsyncModbusTcpClient

async def test():
    c = AsyncModbusTcpClient('172.16.1.90', port=502)
    await c.connect()
    
    # Try different offsets that might be the Process Data
    # 4096 (1000H)
    r = await c.read_holding_registers(address=4096, count=50)
    print("4096:", r.registers if not r.isError() else r)

    # Some devices use 0, but maybe length 50 includes it?
    r = await c.read_holding_registers(address=0, count=125)
    print("0:", r.registers if not r.isError() else r)

    c.close()

asyncio.run(test())
