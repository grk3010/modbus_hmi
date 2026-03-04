import asyncio
from pycomm3 import CIPDriver, Services

master_ip = "172.16.1.90"

def test_identity():
    try:
        with CIPDriver(master_ip) as plc:
            print(f"Connected to {master_ip}")
            # Try to read CIP Identity Object (Class 0x01, Instance 0x01)
            # Attribute 1 = Vendor ID
            # Attribute 7 = Product Name
            for attr in [1, 2, 3, 4, 5, 6, 7]:
                try:
                    res = plc.generic_message(
                        service=Services.get_attribute_single,
                        class_code=0x01,
                        instance=0x01,
                        attribute=attr
                    )
                    if not res.error:
                        print(f"Identity Attr {attr}: {res.value}")
                    else:
                        print(f"Identity Attr {attr} ERROR: {res.error}")
                except Exception as e:
                    print(f"Identity Attr {attr} EXC: {e}")
                    
    except Exception as e:
        print(f"Connection Error: {e}")

if __name__ == "__main__":
    test_identity()
