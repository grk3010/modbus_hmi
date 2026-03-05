import json
import os
from nicegui import ui

from scripts.parsing.sensor_parser import SensorParser
from modbus_client import ModbusClient
from opcua_client import OpcUaClient
from data_logger import DataLogger

SETTINGS_FILE = "hmi_settings.json"
IODD_DIR = "iodd_files"

settings = {"master_type": "NQ-MP8L (8 Ports)"}
settings.update({str(i): "" for i in range(1, 9)})

os.makedirs(IODD_DIR, exist_ok=True)

sensor_parser = SensorParser(iodd_dir=IODD_DIR)
modbus_client = ModbusClient()
opcua_client = OpcUaClient(settings)
data_logger = DataLogger()

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                loaded = json.load(f)
                settings.update(loaded)
        except Exception as e:
            print(f"Error loading settings: {e}")

load_settings()

def save_settings():
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f)
    ui.notify("Settings saved!", type="positive")

def get_effective_units(port_num):
    if settings.get(f"{port_num}_override_units", False):
        temp_unit = settings.get(f"{port_num}_temp_unit", "°C")
        pres_unit = settings.get(f"{port_num}_pres_unit", "kPa")
        flow_unit = settings.get(f"{port_num}_flow_unit", "L/min")
    else:
        temp_unit = settings.get("global_temp_unit", "°C")
        pres_unit = settings.get("global_pres_unit", "kPa")
        flow_unit = settings.get("global_flow_unit", "L/min")
    return temp_unit, pres_unit, flow_unit

def apply_unit_scaling(val, v_type, port_num):
    if not settings.get(f"{port_num}_rescale", False):
        return val
        
    start_u = settings.get(f"{port_num}_scale_from_{v_type}", "")
    temp_u, pres_u = get_effective_units(port_num)
    target_u = temp_u if v_type == 'temp' else pres_u

    if not start_u or not target_u or start_u == target_u:
        return val

    if v_type == 'temp':
        if start_u == '°F' and target_u == '°C': return (val - 32) / 1.8
        elif start_u == '°C' and target_u == '°F': return (val * 1.8) + 32

    if v_type == 'pres':
        kpa = val
        if start_u == 'MPa': kpa = val * 1000
        elif start_u == 'psi': kpa = val * 6.89476
        elif start_u == 'bar': kpa = val * 100
        
        if target_u == 'MPa': return kpa / 1000
        elif target_u == 'psi': return kpa / 6.89476
        elif target_u == 'bar': return kpa / 100
        return kpa

    if v_type == 'flow' or v_type == 'flow_total':
        lpm = val
        if start_u == 'CFM': lpm = val * 28.3168
        
        if target_u == 'CFM': return lpm / 28.3168
        return lpm
        
    return val
