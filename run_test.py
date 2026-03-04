import asyncio
from pymodbus.client import AsyncModbusTcpClient
from modbus_client import ModbusClient
from sensor_parser import SensorParser

async def test():
    p = SensorParser('iodd_files')
    m = ModbusClient()
    c = AsyncModbusTcpClient('172.16.1.90', port=502)
    await c.connect()
    r = await c.read_holding_registers(address=0, count=40)
    
    mp_map = p.get_sensor_map('MP-FR20(R)/MP-FG20(R)/MP-FN20(R)')
    gp_map = p.get_sensor_map('GP-M010T')
    
    print('MP at 8:', m.decode_payload(r.registers[8:20], mp_map))
    print('GP at 5:', m.decode_payload(r.registers[5:8], gp_map))
    
    await c.close()

asyncio.run(test())
