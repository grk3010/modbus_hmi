import asyncio
import logging
from pymodbus.client import AsyncModbusTcpClient
import struct
from pycomm3 import CIPDriver, Services

logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

# Suppress pycomm3 from logging expected connection/service errors during discovery
logging.getLogger('pycomm3').setLevel(logging.CRITICAL)

# Keyence NQ IO-Link Master Modbus register layouts.
# Each master type has a header offset and a fixed block size per port.
MASTER_LAYOUTS = {
    "NQ-EP4L": {"header": 2, "block_size": 16, "max_ports": 4},
    "NQ-MP8L": {"header": 2, "block_size": 16, "max_ports": 8},
}

class ModbusClient:
    def __init__(self, host="127.0.0.1", port=502):
        self.host = host
        self.port = port
        self.client = None
        self.connected = False
        # Each port has 50 words reserved. Port 1 is start_address=0 by default for NQ-EP4L
        self.start_address = 0
        self.words_per_port = 50
        
        # Store latest decoded data for UI
        self.port_data = {i: {} for i in range(1, 9)}
        self.port_raw_data = {i: [] for i in range(1, 9)} # For diagnostic UI
        self.port_status = {i: False for i in range(1, 9)}
        self.master_online = False
        
        # Endianness flags
        self.byte_swap = False
        self.word_swap = False

    @staticmethod
    def get_modbus_layout(master_type, port_num, sensor_map=None):
        """
        Calculate the correct Modbus start address and register count for a given port
        based on the master type's known register layout.
        
        Args:
            master_type: e.g. "NQ-EP4L (4 Ports)" or "NQ-MP8L (8 Ports)"
            port_num: IO-Link port number (1-based)
            sensor_map: optional IODD sensor_map dict to compute exact PDI word count
            
        Returns:
            (address, length) tuple
        """
        # Identify the layout from the master_type string
        layout = None
        for key, val in MASTER_LAYOUTS.items():
            if key in master_type:
                layout = val
                break
        
        if layout is None:
            # Unknown master — fall back to legacy defaults
            return ((port_num - 1) * 50, 50)
        
        address = layout["header"] + (port_num - 1) * layout["block_size"]
        
        # Use IODD sensor map to calculate exact word count, or fall back to full block
        if sensor_map:
            max_bit = max((v["bit_offset"] + v["bit_length"] for v in sensor_map.values()), default=0)
            length = (max_bit + 15) // 16  # ceil division to 16-bit words
        else:
            length = layout["block_size"]
        
        return (address, length)
        
    async def connect(self):
        # If the host changed, tear down the old client so a new one is created
        if self.client is not None and self.client.comm_params.host != self.host:
            self.client.close()
            self.client = None
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
        import ipaddress
        found_devices = []
        
        try:
            if '/' not in base_ip:
                base_ip += '/24'
            network = ipaddress.ip_network(base_ip, strict=False)
            if network.num_addresses > 1024:
                # If the subnet is huge (like /8), restrict to the /24 block of the given IP
                ip_part = base_ip.split('/')[0]
                network = ipaddress.ip_network(f"{ip_part}/24", strict=False)
            test_ips = [str(ip) for ip in network.hosts()]
        except Exception:
            # Fallback if invalid base_ip format
            test_ips = ["127.0.0.1", "192.168.1.100", "192.168.1.101", "10.0.0.100"]
        
        sem = asyncio.Semaphore(20)  # Limit concurrent connections so we don't exhaust file descriptors and overwhelm the network
        
        async def check_ip(ip):
            async with sem:
                try:
                    # Short timeout for scanning
                    client = AsyncModbusTcpClient(ip, port=502, timeout=0.5)
                    connected = await client.connect()
                    if connected:
                        found_devices.append(ip)
                        client.close()
                except Exception:
                    pass
                
        tasks = [check_ip(ip) for ip in test_ips]
        await asyncio.gather(*tasks)
        return found_devices

    async def scan_cip_network(self, broadcast_ip="255.255.255.255", timeout=2.0):
        """Scans the network for Keyence IO-Link masters using EtherNet/IP CIP ListIdentity."""
        import socket
        import time

        def _do_scan():
            PORT = 44818
            # CIP Encapsulation Header for ListIdentity (Command 0x0063)
            list_identity_request = struct.pack(
                '<HHII8sI',
                0x0063,      # Command: ListIdentity
                0x0000,      # Length: 0
                0x00000000,  # Session Handle: 0
                0x00000000,  # Status: 0
                b'\x00'*8,   # Sender Context
                0x00000000   # Options: 0
            )

            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.settimeout(timeout)
            devices_found = []

            try:
                sock.sendto(list_identity_request, (broadcast_ip, PORT))
                start_time = time.time()
                while time.time() - start_time < timeout:
                    try:
                        data, addr = sock.recvfrom(1024)
                        if len(data) >= 24:
                            command = struct.unpack('<H', data[0:2])[0]
                            if command == 0x0063:
                                if len(data) >= 26:
                                    item_count = struct.unpack('<H', data[24:26])[0]
                                    offset = 26
                                    for _ in range(item_count):
                                        if offset + 4 > len(data):
                                            break
                                        item_type, item_length = struct.unpack('<HH', data[offset:offset+4])
                                        offset += 4
                                        if item_type == 0x000C:
                                            target_data = data[offset:offset+item_length]
                                            if len(target_data) >= 33:
                                                vendor_id = struct.unpack('<H', target_data[18:20])[0]
                                                name_len = target_data[32]
                                                if len(target_data) >= 33 + name_len:
                                                    product_name = target_data[33:33+name_len].decode('utf-8', errors='ignore')
                                                    devices_found.append({
                                                        "ip": addr[0],
                                                        "product_name": product_name,
                                                        "vendor_id": vendor_id
                                                    })
                                        offset += item_length
                    except socket.timeout:
                        break
                    except Exception as e:
                        logger.error(f"Error receiving data: {e}")
            finally:
                sock.close()
            return devices_found

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _do_scan)

    async def discover_connected_sensors(self, ip_address, num_ports=8):
        """
        Connects to the IO-Link master via CIP explicit messaging (EtherNet/IP)
        and queries Class 0x0085 (ISDU) to find the connected sensor's Product ID directly.
        If that fails, falls back to Class 0x0304 Attributes 11 and 12.
        Returns a dictionary mapping port number to {product_id_str, vendor_id, device_id}.
        """
        def _do_discover():
            sensors = {}
            try:
                with CIPDriver(ip_address) as master:
                    for port in range(1, num_ports + 1):
                        try:
                            port_info = {}
                            
                            # First attempt: ISDU Read (Class 0x85) for Product ID (Index 0x0013)
                            # Keyence NQ requires little-endian for the Index (0x13 0x00) and 1 byte sub-index (0x00)
                            req_data = (0x0013).to_bytes(2, byteorder='little') + (0).to_bytes(1, byteorder='big')
                            
                            isdu_resp = master.generic_message(
                                service=0x4B, # ISDU_Read
                                class_code=0x85,
                                instance=0x01,
                                attribute=port,
                                request_data=req_data
                            )
                            
                            if isdu_resp and not isdu_resp.error and isdu_resp.value:
                                product_id_str = isdu_resp.value.decode('utf-8', errors='ignore').strip('\x00')
                                if product_id_str:
                                    port_info["product_id_str"] = product_id_str

                            # Second attempt: Read Vendor ID -> Class 0x0304, Instance = Port, Attribute 11 (0x0B)
                            vendor_resp = master.generic_message(
                                service=Services.get_attribute_single,
                                class_code=0x0304,
                                instance=port,
                                attribute=11
                            )
                            
                            # Read Device ID -> Class 0x0304, Instance = Port, Attribute 12 (0x0C)
                            device_resp = master.generic_message(
                                service=Services.get_attribute_single,
                                class_code=0x0304,
                                instance=port,
                                attribute=12
                            )
                            
                            if vendor_resp and device_resp and vendor_resp.value and device_resp.value:
                                # Convert the bytes to integers (Little Endian)
                                vendor_id = int.from_bytes(vendor_resp.value, byteorder='little')
                                device_id = int.from_bytes(device_resp.value, byteorder='little')
                                
                                if vendor_id != 0 or device_id != 0:
                                    port_info["vendor_id"] = vendor_id
                                    port_info["device_id"] = device_id
                            
                            if port_info:
                                sensors[port] = port_info

                        except Exception as port_e:
                            logger.error(f"Failed to read port {port} via CIP on {ip_address}: {port_e}")
            except Exception as e:
                logger.error(f"Failed to connect to CIP on {ip_address} for discovery: {e}")
                
            return sensors

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _do_discover)

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

        # Pad registers to match the sensor's maximum bit offset map
        max_bit = max([v["bit_offset"] + v["bit_length"] for v in sensor_map.values()]) if sensor_map else 0
        expected_words = (max_bit + 15) // 16
        padded_registers = list(raw_registers)
        if len(padded_registers) < expected_words:
            padded_registers.extend([0] * (expected_words - len(padded_registers)))

        # Apply byte/word swaps if configured
        swapped_registers = []
        for reg in padded_registers:
            val = reg
            if self.byte_swap:
                val = ((val << 8) & 0xFF00) | ((val >> 8) & 0x00FF)
            swapped_registers.append(val)
        
        if self.word_swap:
            # Swap adjacent 16-bit words (typical for 32-bit values)
            for i in range(0, len(swapped_registers) - 1, 2):
                swapped_registers[i], swapped_registers[i+1] = swapped_registers[i+1], swapped_registers[i]

        # Convert registers to a single byte stream, assuming Big Endian for Modbus TCP
        # pymodbus returns registers as ints, we pack them into bytes
        payload_bytes = b"".join(struct.pack(">H", reg) for reg in swapped_registers)
        total_bits = len(payload_bytes) * 8


            
        # Calculate total required payload bits instead of full padded len
        total_payload_bits = max_bit if max_bit > 0 else len(payload_bytes) * 8
        
        # IO-Link transmits bit N first and bit 0 last. 
        # Modbus maps the first received word to the first register.
        # This means the highest bit index (e.g. 191) is in the first byte.
        # So we crop payload_bytes to just the actual payload size
        byte_len = (total_payload_bits + 7) // 8
        actual_payload_bytes = payload_bytes[:byte_len]
        
        # Convert bytes to a single massive integer for easy bit shifting
        payload_int = int.from_bytes(actual_payload_bytes, byteorder='big')
        
        decoded_data = {}
        for var_name, var_info in sensor_map.items():
            bit_offset = var_info["bit_offset"]
            bit_length = var_info["bit_length"]
            datatype = var_info["datatype"]
            
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
            self.byte_swap = hmi_settings.get("byte_swap", False)
            self.word_swap = hmi_settings.get("word_swap", False)
            
            master_type = hmi_settings.get("master_type", "NQ-MP8L")
            max_ports = 8 if "8" in master_type else 4

            for port_str, product_id in hmi_settings.items():
                if port_str in ["master_type", "master_ip"] or "_" in port_str or not product_id:
                    continue
                    
                port_num = int(port_str)
                if port_num > max_ports:
                    continue

                addr_default = self.start_address + ((port_num - 1) * self.words_per_port)
                address = int(hmi_settings.get(f"{port_num}_modbus_address", addr_default))
                count = int(hmi_settings.get(f"{port_num}_modbus_length", self.words_per_port))
                
                try:
                    # Read defined registers per port
                    response = await self.client.read_holding_registers(address=address, count=count)
                    if not response.isError():
                        self.port_raw_data[port_num] = response.registers
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

    async def write_valve(self, port_num: int, state: bool):
        """
        Writes to the IO-Link master's Process Data Out register.
        For the Keyence MP-F, when 'Valve Control Mode' is 'External Input Control',
        Bit 0 = Open Valve, Bit 1 = Close Valve.
        """
        if not self.connected:
            return False
            
        # Keyence NQ Modbus mapping for Process Data Out starts at 2049
        address = 2049 + ((port_num - 1) * 16)
        
        # bitOffset 0 (Bit 0) = Valve Open -> Decimal 1
        # bitOffset 1 (Bit 1) = Valve Close -> Decimal 2
        val = 1 if state else 2
        
        try:
            response = await self.client.write_register(address, val)
            return not response.isError()
        except Exception as e:
            logger.error(f"Error writing valve to port {port_num}: {e}")
            return False

    async def reset_accumulated_flow(self, port_num: int):
        """
        Resets the accumulated flow on Keyence MP-F sensors.
        Sends a CIP explicit message to IO-Link ISDU Index 600, Subindex 0 with value 0.
        """
        def _do_reset():
            try:
                with CIPDriver(self.host) as master:
                    # ISDU Write (Service 0x4C)
                    # Index 600 = 0x0258. CIP expects LE: 0x58 0x02
                    # Subindex 0 = 0x00
                    # Data: 0 (1 byte for Accumulated Flow Reset command)
                    req_data = (600).to_bytes(2, byteorder='little') + (0).to_bytes(1, byteorder='big') + (0).to_bytes(1, byteorder='big')
                    
                    resp = master.generic_message(
                        service=0x4C, # ISDU_Write
                        class_code=0x85,
                        instance=0x01,
                        attribute=port_num,
                        request_data=req_data
                    )
                    return resp and not resp.error
            except Exception as e:
                logger.error(f"Failed to reset flow on port {port_num} via CIP: {e}")
                return False

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _do_reset)

if __name__ == "__main__":
    from scripts.parsing.sensor_parser import SensorParser
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
