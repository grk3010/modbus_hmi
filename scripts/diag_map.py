"""
CIP attribute probe: discovers what the NQ-EP4L exposes about its Modbus/IO-Link layout.
Queries Class 0x0304 (IO-Link Port) and other relevant classes for PDI size info.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pycomm3 import CIPDriver, Services
import struct
import logging
logging.getLogger('pycomm3').setLevel(logging.CRITICAL)

MASTER_IP = "172.16.1.171"

def probe_port_attributes(master, port, class_code=0x0304):
    """Read all plausible attributes for a port instance."""
    results = {}
    for attr in range(1, 30):
        try:
            resp = master.generic_message(
                service=Services.get_attribute_single,
                class_code=class_code,
                instance=port,
                attribute=attr
            )
            if resp and not resp.error and resp.value:
                raw = resp.value
                # Try interpreting as int (little-endian)
                if len(raw) == 1:
                    val = raw[0]
                elif len(raw) == 2:
                    val = int.from_bytes(raw, 'little')
                elif len(raw) == 4:
                    val = int.from_bytes(raw, 'little')
                else:
                    val = raw.hex()
                results[attr] = {"raw": raw.hex(), "int": val, "len": len(raw)}
        except Exception:
            pass
    return results

def probe_class_attributes(master, class_code):
    """Read class-level attributes (instance 0)."""
    results = {}
    for attr in range(1, 20):
        try:
            resp = master.generic_message(
                service=Services.get_attribute_single,
                class_code=class_code,
                instance=0,
                attribute=attr
            )
            if resp and not resp.error and resp.value:
                raw = resp.value
                if len(raw) <= 4:
                    val = int.from_bytes(raw, 'little')
                else:
                    val = raw.hex()
                results[attr] = {"raw": raw.hex(), "int": val, "len": len(raw)}
        except Exception:
            pass
    return results

def main():
    with CIPDriver(MASTER_IP) as master:
        print(f"Connected to {MASTER_IP}\n")

        # Probe Class 0x0304 (IO-Link Port) — class-level attributes
        print("=== Class 0x0304 (IO-Link Port) — Class Level (Instance 0) ===")
        cls_attrs = probe_class_attributes(master, 0x0304)
        for attr, info in sorted(cls_attrs.items()):
            print(f"  Attr {attr:2d}: raw={info['raw']:20s}  int={info['int']}  len={info['len']}")

        # Probe each port instance (1-4 for EP4L)
        for port in range(1, 5):
            print(f"\n=== Class 0x0304, Port {port} ===")
            attrs = probe_port_attributes(master, port, 0x0304)
            for attr, info in sorted(attrs.items()):
                print(f"  Attr {attr:2d}: raw={info['raw']:20s}  int={info['int']}  len={info['len']}")

        # Also probe Class 0x0085 (ISDU) class-level for any layout info
        print(f"\n=== Class 0x0085 (ISDU) — Class Level (Instance 0) ===")
        cls_attrs2 = probe_class_attributes(master, 0x0085)
        for attr, info in sorted(cls_attrs2.items()):
            print(f"  Attr {attr:2d}: raw={info['raw']:20s}  int={info['int']}  len={info['len']}")

        # Probe Assembly Object (Class 0x04) — often holds I/O mapping info
        print(f"\n=== Class 0x04 (Assembly) — Class Level ===")
        cls_attrs3 = probe_class_attributes(master, 0x04)
        for attr, info in sorted(cls_attrs3.items()):
            print(f"  Attr {attr:2d}: raw={info['raw']:20s}  int={info['int']}  len={info['len']}")

        # Probe Assembly instances 1-10
        for inst in range(1, 11):
            attrs = {}
            for attr in [1, 2, 3, 4]:
                try:
                    resp = master.generic_message(
                        service=Services.get_attribute_single,
                        class_code=0x04,
                        instance=inst,
                        attribute=attr
                    )
                    if resp and not resp.error and resp.value:
                        raw = resp.value
                        if len(raw) <= 4:
                            val = int.from_bytes(raw, 'little')
                        else:
                            val = f"({len(raw)}B) {raw[:20].hex()}..."
                        attrs[attr] = {"int": val, "len": len(raw)}
                except Exception:
                    pass
            if attrs:
                print(f"  Assembly Instance {inst}: {attrs}")

if __name__ == "__main__":
    main()
