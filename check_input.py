import asyncio
from pymodbus.client import AsyncModbusTcpClient

async def test():
    c = AsyncModbusTcpClient('172.16.1.90', port=502)
    await c.connect()
    
    # Process Data IN might be Input Registers (FC 4), at 0 or 4096 (1000H)
    r1 = await c.read_input_registers(address=0, count=125)
    print("0 INPUT:", r1.registers if not r1.isError() else r1)
    
    r2 = await c.read_input_registers(address=4096, count=16)
    print("4096 INPUT:", r2.registers if not r2.isError() else r2)

    c.close()

asyncio.run(test())
