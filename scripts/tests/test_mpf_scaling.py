import asyncio
from modbus_client import ModbusClient
import json

async def test():
    with open("hmi_settings.json", "r") as f:
        settings = json.load(f)
        
    client = ModbusClient(settings.get("master_ip", "172.16.1.90"))
    await client.connect()
    
    from sensor_parser import SensorParser
    parser = SensorParser()
    
    address = client.start_address + (2 * client.words_per_port)
    try:
        res = await client.client.read_holding_registers(address=address, count=50)
        if not res.isError():
            print(f"Raw Registers: {res.registers}")
            mp_map = parser.get_sensor_map("MP-FR80/MP-FG80/MP-FN80")
            print(f"Map: {mp_map}")
            decoded = client.decode_payload(res.registers, mp_map)
            print(f"Decoded: {decoded}")
        else:
            print("Error reading registers")
    except Exception as e:
        print(f"Exception: {e}")
        
    client.disconnect()

asyncio.run(test())
