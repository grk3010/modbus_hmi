import asyncio
import sys
from pycomm3 import CIPDriver, Services

def read_class_304(ip, port, attribute):
    try:
        with CIPDriver(ip) as plc:
            # Service code 0E = Get Attribute Single
            res = plc.generic_message(
                service=Services.get_attribute_single,
                class_code=0x0304,
                instance=port,
                attribute=attribute
            )
            
            if not res.error:
                return res.value
            else:
                return f"ERROR: {res.error}"
    except Exception as e:
        return f"EXCEPTION: {e}"

if __name__ == "__main__":
    ip = "172.16.1.90"
    for port in range(1, 9):
        print(f"--- Port {port} ---")
        vendor_id = read_class_304(ip, port, 11) # 0x0B Vendor ID for validation
        print(f"Vendor ID for validation: {vendor_id}")
        device_id = read_class_304(ip, port, 12) # 0x0C Device ID for validation
        print(f"Device ID for validation: {device_id}")
        
        # Test 0x1C (Input data word 0) just to see if we can read it
        input_data = read_class_304(ip, port, 28)
        print(f"Input data word 0: {input_data}")
