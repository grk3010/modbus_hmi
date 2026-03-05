import asyncio
from modbus_client import ModbusClient
from sensor_parser import SensorParser

async def test():
    parser = SensorParser()
    client = ModbusClient()
    
    fake_registers = [1500] + [0]*49
    mp_map = parser.get_sensor_map("MP-FR80/MP-FG80/MP-FN80")
    decoded = client.decode_payload(fake_registers, mp_map)
    print("Decoded Fake MP-FN80:", decoded)

if __name__ == "__main__":
    asyncio.run(test())
