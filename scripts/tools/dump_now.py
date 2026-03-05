import asyncio
from pymodbus.client import AsyncModbusTcpClient
async def test():
    c = AsyncModbusTcpClient('172.16.1.90', port=502)
    await c.connect()
    r = await c.read_input_registers(address=0, count=25)
    print(r.registers if not r.isError() else r)
    c.close()
asyncio.run(test())
