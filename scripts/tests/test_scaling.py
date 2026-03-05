import json

def get_effective_units(port_num, settings):
    if settings.get(f"{port_num}_override_units", False):
        temp_unit = settings.get(f"{port_num}_temp_unit", "°C")
        pres_unit = settings.get(f"{port_num}_pres_unit", "kPa")
        flow_unit = settings.get(f"{port_num}_flow_unit", "L/min")
    else:
        temp_unit = settings.get("global_temp_unit", "°C")
        pres_unit = settings.get("global_pres_unit", "kPa")
        flow_unit = settings.get("global_flow_unit", "L/min")
    return temp_unit, pres_unit, flow_unit

def apply_unit_scaling(val, v_type, port_num, settings):
    if not settings.get(f"{port_num}_rescale", False):
        return val
        
    start_u = settings.get(f"{port_num}_scale_from_{v_type}", "")
    temp_u, pres_u, flow_u = get_effective_units(port_num, settings)
    
    if v_type == 'temp': target_u = temp_u
    elif v_type == 'pres': target_u = pres_u
    else: target_u = flow_u

    print(f"scaling {val} from {start_u} to {target_u}")
    
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

with open('hmi_settings.json') as f:
    s = json.load(f)

print(apply_unit_scaling(771.0, 'pres', 2, s))
print(apply_unit_scaling(199.0, 'flow', 1, s))
