import sys
from pycomm3 import CIPDriver, Services

def test_isdu(ip, port, index, subindex=0):
    try:
        with CIPDriver(ip) as plc:
            # The manual says: Attribute ID = port (01 to 08)
            # Service Data = Index (XX XX) + Sub-index (XX)
            req_data_big = index.to_bytes(2, byteorder='big') + subindex.to_bytes(1, byteorder='big')
            req_data_little = index.to_bytes(2, byteorder='little') + subindex.to_bytes(1, byteorder='big')
            
            for req in [req_data_big, req_data_little]:
                print(f"Testing req_data: {req.hex()}")
                res = plc.generic_message(
                    service=0x4B,
                    class_code=0x85,
                    instance=0x01,
                    attribute=port,
                    request_data=req
                )
                if not res.error:
                    print(f"SUCCESS! Data: {res.value.hex() if res.value else 'empty'} | as String: {res.value}")
                else:
                    print(f"ERROR: {res.error}")
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    ip = "172.16.1.90"
    print("Testing Port 1 Index 0x0010 (Vendor Name):")
    test_isdu(ip, 1, 0x0010)
    print("Testing Port 1 Index 0x0011 (Vendor Text):")
    test_isdu(ip, 1, 0x0011)
    print("Testing Port 1 Index 0x0012 (Product Name):")
    test_isdu(ip, 1, 0x0012)
    print("Testing Port 1 Index 0x0013 (Product ID):")
    test_isdu(ip, 1, 0x0013)
