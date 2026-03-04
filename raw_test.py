import asyncio
from pymodbus.client import AsyncModbusTcpClient
async def test():
    c = AsyncModbusTcpClient('172.16.1.90', port=502)
    await c.connect()
    r = await c.read_holding_registers(address=0, count=20)
    print("Registers:", r.registers)
    await c.close()
asyncio.run(test())
