import sys
from pycomm3 import CIPDriver, Services

def scan_attributes(ip, instance, stop_attr=50):
    try:
        with CIPDriver(ip) as plc:
            print(f"--- Scanning Instance {instance} ---")
            for attr in range(1, stop_attr + 1):
                res = plc.generic_message(
                    service=Services.get_attribute_single,
                    class_code=0x0304,
                    instance=instance,
                    attribute=attr
                )
                if not res.error:
                    val_hex = res.value.hex() if res.value else "EMPTY"
                    print(f"Attr {attr} (Dec) | {hex(attr)} (Hex): {val_hex}")
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    ip = "172.16.1.90"
    for port in range(1, 5):
        scan_attributes(ip, port, 50)
