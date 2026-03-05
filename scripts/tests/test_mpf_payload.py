import struct
from modbus_client import ModbusClient
from sensor_parser import SensorParser

parser = SensorParser()
client = ModbusClient()

# Known raw registers from the test run
raw = [587, 8560, 6, 2, 8546, 29, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

mp_map = parser.get_sensor_map("MP-FR80/MP-FG80/MP-FN80")

decoded = client.decode_payload(raw, mp_map)
print("Decoded Test:", decoded)

def my_decode(raw, sensor_map):
    # NQ-EP4L / MP8L Modbus TCP Mapping
    # The first register represents the first 16 bits of the payload.
    # IO-Link standard puts Bit 0 at the end of the payload.
    # If the MP-F payload is 24 bytes (192 bits), 
    if not raw or not sensor_map:
        return {}

    # Just pad to 50 words as passed
    payload_bytes = b"".join(struct.pack(">H", reg) for reg in raw)
    
    # Actually, the MP-F payload is 192 bits (12 words).
    # If the master sends the process data starting at word 0, 
    # the 192 bits are in the first 12 words.
    
    # IO-Link bit offsets are usually mapped such that bit 191 is the first bit transmitted,
    # and bit 0 is the last bit transmitted. 
    # For a 192-bit payload, the first byte received contains bits 184-191.
    
    total_payload_bits = 192 # Known for MP-F
    actual_payload_bytes = payload_bytes[:total_payload_bits // 8]
    
    payload_int = int.from_bytes(actual_payload_bytes, byteorder='big')
    decoded_data = {}
    for var_name, var_info in sensor_map.items():
        bit_offset = var_info["bit_offset"]
        bit_length = var_info["bit_length"]
        datatype = var_info["datatype"]
        
        shifted = payload_int >> bit_offset
        mask = (1 << bit_length) - 1
        raw_val = shifted & mask
        
        if datatype == "IntegerT" and (raw_val & (1 << (bit_length - 1))):
            raw_val -= (1 << bit_length)
            
        decoded_data[var_name] = raw_val
        
    return decoded_data

print("My Decode:", my_decode(raw, mp_map))

