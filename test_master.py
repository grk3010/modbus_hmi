import asyncio
from pymodbus.client import AsyncModbusTcpClient
import modbus_client
from sensor_parser import SensorParser

async def test():
    parser = SensorParser(iodd_dir="iodd_files")
    client = modbus_client.ModbusClient()
    
    tcp = AsyncModbusTcpClient("172.16.1.90", port=502)
    conn = await tcp.connect()
    res = await tcp.read_holding_registers(address=0, count=125)
    regs = res.registers
    
    print("Trying to find MP-F at different offsets")
    mp_map = parser.get_sensor_map("MP-FR80/MP-FG80/MP-FN80")
    for offset in range(0, 100):
        sliced = regs[offset:offset+20]
        decoded = client.decode_payload(sliced, mp_map)
        # FlowInst, Pressure, Temp
        f = decoded.get('1FlowInst', 0)
        p = decoded.get('1Pressure', 0)
        t = decoded.get('1Temperature', 0)
        
        # Temp is usually ~200-300 (20.0 - 30.0 C)
        # Or Pressure is nearby
        if 100 < t < 500 or 10 < p < 500 or f > 0:
            print(f"MP Offset {offset}: {decoded}")

    print("Trying to find GP-M at different offsets")
    gp_map = parser.get_sensor_map("GP-M010T")
    for offset in range(0, 100):
        sliced = regs[offset:offset+4]
        decoded = client.decode_payload(sliced, gp_map)
        p = decoded.get('Pressure', 0)
        t = decoded.get('Temp', 0)
        if 100 < t < 500 or p > 0:
            print(f"GP Offset {offset}: {decoded}")
            
    tcp.close()

asyncio.run(test())
