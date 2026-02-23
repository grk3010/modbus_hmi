import asyncio
import logging
from pymodbus.client import AsyncModbusTcpClient
import struct

logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

class ModbusClient:
    def __init__(self, host="127.0.0.1", port=502):
        self.host = host
        self.port = port
        self.client = None
        self.connected = False
        # Each port has 50 words reserved. Port 1 is start_address=1000
        self.start_address = 1000
        self.words_per_port = 50
        
        # Store latest decoded data for UI
        self.port_data = {i: {} for i in range(1, 9)}
        self.port_status = {i: False for i in range(1, 9)}
        self.master_online = False
        
    async def connect(self):
        if self.client is None:
            self.client = AsyncModbusTcpClient(self.host, port=self.port)
        self.connected = await self.client.connect()
        if not self.connected:
            logger.error(f"Failed to connect to Modbus Master at {self.host}:{self.port}")
        return self.connected
        
    def disconnect(self):
        if self.connected:
            self.client.close()
            self.connected = False

    async def scan_network(self, base_ip="192.168.1.0/24"):
        """Scans the network for Modbus devices responding on port 502."""
        found_devices = []
        # Basic implementation: try common IPs or a quick ping sweep if base_ip is given.
        # For this MVP, we will just try a few local addresses as a proof of concept
        # or rely on manual entry for strict environments.
        test_ips = ["127.0.0.1", "192.168.1.100", "192.168.1.101", "10.0.0.100"]
        
        async def check_ip(ip):
            try:
                # Short timeout for scanning
                client = AsyncModbusTcpClient(ip, port=502, timeout=1.0)
                connected = await client.connect()
                if connected:
                    # Attempt to read generic device ID or just assume it's a target if 502 is open
                    found_devices.append(ip)
                    client.close()
            except Exception:
                pass
                
        tasks = [check_ip(ip) for ip in test_ips]
        await asyncio.gather(*tasks)
        return found_devices

    def decode_payload(self, raw_registers, sensor_map):
        """
        Decodes a list of 16-bit registers returned by Modbus into sensor values
        based on the IODD sensor_map dictionary.
        
        Args:
            raw_registers: list of integers (the holding registers)
            sensor_map: dict of mapped variables from SensorParser
        """
        if not raw_registers or not sensor_map:
            return {}

        # Convert registers to a single byte stream, assuming Big Endian for Modbus TCP
        # pymodbus returns registers as ints, we pack them into bytes
        payload_bytes = b"".join(struct.pack(">H", reg) for reg in raw_registers)
        total_bits = len(payload_bytes) * 8

        decoded_data = {}
        for var_name, var_info in sensor_map.items():
            bit_offset = var_info["bit_offset"]
            bit_length = var_info["bit_length"]
            datatype = var_info["datatype"]
            
            # Keyence Process data is usually Big Endian. 
            # The bit_offset in IO-Link is usually from the end of the payload.
            # Example: 192 bit payload. bit_offset=176, length=16. 
            # This corresponds to bit indices (192-176-16) = 0 to 15.
            
            # Standard IO-Link bit positioning: bit offset 0 is in the LSB of the last byte.
            # However, mapping into Modbus registers means the first byte of payload 
            # might correspond to the MSB of the highest addressed word.
            # To simplify, we shift the entire payload by the bit offset.
            
            # Convert bytes to a massive int
            payload_int = int.from_bytes(payload_bytes, byteorder='big')
            
            # Shift down to make this variable the LSB
            shifted = payload_int >> bit_offset
            
            # Mask out the length
            mask = (1 << bit_length) - 1
            raw_val = shifted & mask
            
            # Handle signed integers
            if datatype == "IntegerT":
                # If the MSB is 1, it's negative
                if raw_val & (1 << (bit_length - 1)):
                    raw_val -= (1 << bit_length)
            
            # For this MVP, we won't apply complex Gradients/Offsets, we just return raw.
            # Real applications would multiply by Gradient and add Offset defined in XML.
            decoded_data[var_name] = raw_val

        return decoded_data

    def _extract_bits(self, data_bytes, start_bit, bit_length):
        """Extracts an integer from a byte array given a start bit and length."""
        # Convert byte array to an integer
        int_val = int.from_bytes(data_bytes, byteorder='big')
        # Shift right to eliminate trailing bits
        total_bits = len(data_bytes) * 8
        shift_amount = total_bits - (start_bit + bit_length)
        shifted = int_val >> shift_amount
        # Mask out leading bits
        mask = (1 << bit_length) - 1
        return shifted & mask

    async def poll_ports(self, hmi_settings, sensor_parser):
        """
        Continuously polls ports that are configured in hmi_settings.
        """
        while True:
            target_ip = hmi_settings.get("master_ip", "127.0.0.1")
            
            if not self.connected or self.host != target_ip:
                self.host = target_ip
                await self.connect()

            if not self.connected:
                self.master_online = False
                for i in range(1, 9):
                    self.port_status[i] = False
                await asyncio.sleep(2)
                continue
                
            self.master_online = True
            master_type = hmi_settings.get("master_type", "NQ-MP8L")
            max_ports = 8 if "8" in master_type else 4

            for port_str, product_id in hmi_settings.items():
                if port_str in ["master_type", "master_ip"] or not product_id:
                    continue
                    
                port_num = int(port_str)
                if port_num > max_ports:
                    continue

                address = self.start_address + ((port_num - 1) * self.words_per_port)
                
                try:
                    # Read 50 registers per port (covers max IO-Link process data)
                    response = await self.client.read_holding_registers(address, self.words_per_port)
                    if not response.isError():
                        sensor_map = sensor_parser.get_sensor_map(product_id)
                        decoded = self.decode_payload(response.registers, sensor_map)
                        self.port_data[port_num] = decoded
                        self.port_status[port_num] = True
                    else:
                        self.port_status[port_num] = False
                        logger.error(f"Error reading port {port_num}")
                except Exception as e:
                    self.port_status[port_num] = False
                    logger.error(f"Exception polling port {port_num}: {e}")
                    # If this throws, maybe disconnected? Let loop handle reconnect
                    self.connected = False

            # Polling delay
            await asyncio.sleep(0.5)

if __name__ == "__main__":
    from sensor_parser import SensorParser
    # manual test
    parser = SensorParser()
    client = ModbusClient()
    
    # Fake 16-bit registers simulating a Payload for an MP-F. 
    # MP-F80 has Flow at bit_offset 176 (Length 16).
    # This means total bits = 192 (12 words).
    # (192-176-16) = 0 start bit. So it's the very first register.
    fake_registers = [1500] + [0]*49 # First register is 1500 (Flow)
    
    mp_map = parser.get_sensor_map("MP-FR80/MP-FG80/MP-FN80")
    decoded = client.decode_payload(fake_registers, mp_map)
    print("Decoded Fake MP-FN80:", decoded)
