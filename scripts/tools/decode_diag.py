#!/usr/bin/env python3
"""
Diagnostic: Read MP-F Modbus registers and try different decode options
to find the correct mapping. Run from project root: python scripts/tools/decode_diag.py

Set master_ip in hmi_settings.json or pass as arg: python decode_diag.py 172.16.1.171
"""
import sys
import json
import struct
import asyncio

# Add project root
sys.path.insert(0, ".")
from modbus_client import ModbusClient
from scripts.parsing.sensor_parser import SensorParser


def decode_variants(raw_registers, sensor_map):
    """Try different decode variants and return all results."""
    results = {}
    max_bit = max(v["bit_offset"] + v["bit_length"] for v in sensor_map.values())
    byte_len = (max_bit + 7) // 8

    # Variant 1: Standard (big-endian, no reverse)
    regs = list(raw_registers[:12])  # first 12 words
    payload_bytes = b"".join(struct.pack(">H", r) for r in regs)[:byte_len]
    payload_int = int.from_bytes(payload_bytes, byteorder='big')
    results["std (BE, reg 0-11)"] = _extract_all(payload_int, sensor_map)

    # Variant 2: Reverse word order
    regs_rev = list(reversed(regs))
    payload_bytes = b"".join(struct.pack(">H", r) for r in regs_rev)[:byte_len]
    payload_int = int.from_bytes(payload_bytes, byteorder='big')
    results["reverse words"] = _extract_all(payload_int, sensor_map)

    # Variant 3: Little-endian byte order
    payload_bytes = b"".join(struct.pack(">H", r) for r in regs)[:byte_len]
    payload_int = int.from_bytes(payload_bytes, byteorder='little')
    results["little-endian bytes"] = _extract_all(payload_int, sensor_map)

    # Variant 4: Skip 6 words (header), then standard
    regs_skip6 = list(raw_registers[6:18])
    payload_bytes = b"".join(struct.pack(">H", r) for r in regs_skip6)[:byte_len]
    payload_int = int.from_bytes(payload_bytes, byteorder='big')
    results["skip 6, std"] = _extract_all(payload_int, sensor_map)

    # Variant 5: Skip 6, reverse words
    regs_skip6_rev = list(reversed(regs_skip6))
    payload_bytes = b"".join(struct.pack(">H", r) for r in regs_skip6_rev)[:byte_len]
    payload_int = int.from_bytes(payload_bytes, byteorder='big')
    results["skip 6, reverse words"] = _extract_all(payload_int, sensor_map)

    return results


def _extract_all(payload_int, sensor_map):
    out = {}
    for var_name, var_info in sensor_map.items():
        bit_offset = var_info["bit_offset"]
        bit_length = var_info["bit_length"]
        datatype = var_info["datatype"]
        shifted = payload_int >> bit_offset
        mask = (1 << bit_length) - 1
        raw_val = shifted & mask
        if datatype == "IntegerT" and bit_length and (raw_val & (1 << (bit_length - 1))):
            raw_val -= (1 << bit_length)
        out[var_name] = raw_val
    return out


async def main():
    # Load settings for master IP
    try:
        with open("hmi_settings.json") as f:
            settings = json.load(f)
        master_ip = settings.get("master_ip", "172.16.1.171")
    except Exception:
        master_ip = sys.argv[1] if len(sys.argv) > 1 else "172.16.1.171"

    print(f"Connecting to {master_ip}:502 ...")
    client = ModbusClient(host=master_ip)
    ok = await client.connect()
    if not ok:
        print("Failed to connect")
        return

    # Read port 1 (address 0, 50 registers)
    addr = int(settings.get("1_modbus_address", 0))
    count = int(settings.get("1_modbus_length", 50))
    async with client._modbus_lock:
        resp = await client.client.read_holding_registers(address=addr, count=count)

    if resp.isError():
        print("Read error:", resp)
        return

    raw = resp.registers
    print(f"\nRaw registers (first 16): {' '.join(f'{r:04X}' for r in raw[:16])}")
    print(f"As decimal: {raw[:16]}\n")

    parser = SensorParser(iodd_dir="iodd_files")
    sensor_map = parser.get_sensor_map("MP-FR20(R)/MP-FG20(R)/MP-FN20(R)")
    if not sensor_map:
        sensor_map = parser.get_sensor_map("MP-FR80/MP-FG80/MP-FN80")

    print("Decode variants (key values; expect Temp~811 for 81.1°F, Pres~-2 for -0.2 psi):")
    print("-" * 70)
    for name, decoded in decode_variants(raw, sensor_map).items():
        flow = decoded.get("1FlowInst", decoded.get("InstantaneousFlow", "?"))
        pres = decoded.get("1Pressure", decoded.get("Pressure", "?"))
        temp = decoded.get("1Temperature", decoded.get("Temperature", "?"))
        hum = decoded.get("1Humidity", decoded.get("Humidity", "?"))
        print(f"{name:30} Flow={flow:6} Pres={pres:6} Temp={temp:6} Hum={hum}")
    print("-" * 70)
    print("\nLook for the row where Temp≈811 (81.1°F) and Pres≈-2 (-0.2 psi).")
    print("Use that variant's settings in Config.")


if __name__ == "__main__":
    asyncio.run(main())
