import asyncio
from pymodbus.client import AsyncModbusTcpClient
from modbus_client import ModbusClient
from sensor_parser import SensorParser

async def test():
    p = SensorParser('iodd_files')
    m = ModbusClient()
    c = AsyncModbusTcpClient('172.16.1.90', port=502)
    await c.connect()
    
    # Port 1 Process Data In is at 4096 (1000H)
    # Port 2 Process Data In is at 4112 (1010H)
    r_port1 = await c.read_holding_registers(address=4096, count=16)
    r_port2 = await c.read_holding_registers(address=4112, count=16)
    
    print("Port 1 Registers:", r_port1.registers if not r_port1.isError() else "Error")
    print("Port 2 Registers:", r_port2.registers if not r_port2.isError() else "Error")
    
    mp_map = p.get_sensor_map('MP-FR20(R)/MP-FG20(R)/MP-FN20(R)')
    gp_map = p.get_sensor_map('GP-M010T')
    
    if not r_port1.isError():
        print('MP at Port 1:', m.decode_payload(r_port1.registers, mp_map))
    if not r_port2.isError():
        print('GP at Port 2:', m.decode_payload(r_port2.registers, gp_map))
        
    await c.close()

asyncio.run(test())
