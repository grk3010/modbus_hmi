import json
import os
import asyncio
from nicegui import ui, app

from sensor_parser import SensorParser
from modbus_client import ModbusClient

# Paths
SETTINGS_FILE = "hmi_settings.json"
IODD_DIR = "iodd_files"

# Global state
settings = {"master_type": "NQ-MP8L (8 Ports)"}
settings.update({str(i): "" for i in range(1, 9)})
sensor_parser = SensorParser(iodd_dir=IODD_DIR)
modbus_client = ModbusClient()

# Serve extracted images
os.makedirs(IODD_DIR, exist_ok=True)
app.add_static_files('/iodd_assets', os.path.abspath(IODD_DIR))

# Load settings
if os.path.exists(SETTINGS_FILE):
    try:
        with open(SETTINGS_FILE, "r") as f:
            loaded = json.load(f)
            settings.update(loaded)
    except Exception as e:
        print(f"Error loading settings: {e}")

def save_settings():
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f)
    ui.notify("Settings saved!", type="positive")

class ValveToggle(ui.element):
    def __init__(self, port_num, initial_state=False, client=None):
        super().__init__('div')
        self.port_num = port_num
        self.state = initial_state
        self.modbus_client = client
        self.classes('relative inline-flex items-center w-[168px] h-[72px] rounded-full cursor-pointer transition-all duration-300 border-4 border-solid shadow-sm select-none shrink-0')
        self.on('click', self.toggle)
        
        with self:
            self.thumb = ui.element('div').classes('absolute w-[54px] h-[54px] bg-white rounded-full shadow-md transition-all duration-300 z-10')
            self.lbl = ui.label('').classes('absolute text-white font-bold text-lg tracking-wider pointer-events-none transition-all duration-300 z-0')
            
        self._update_appearance()

    def toggle(self):
        self.state = not self.state
        self._update_appearance()
        if self.modbus_client:
            import asyncio
            asyncio.create_task(self.modbus_client.write_valve(self.port_num, self.state))

    def _update_appearance(self):
        if self.state:
            self.classes(remove='border-white bg-[#303030]', add='border-[#20c997] bg-[#20c997]')
            self.thumb.classes(remove='left-[8px]', add='left-[102px]')
            self.lbl.set_text('OPEN')
            self.lbl.classes(remove='right-[16px]', add='left-[16px]')
        else:
            self.classes(remove='border-[#20c997] bg-[#20c997]', add='border-white bg-[#303030]')
            self.thumb.classes(remove='left-[102px]', add='left-[8px]')
            self.lbl.set_text('CLOSED')
            self.lbl.classes(remove='left-[16px]', add='right-[16px]')

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

# --- UI Styling ---
ui.add_head_html("""
<style>
    body {
        background-color: #121212;
        color: #e0e0e0;
        font-family: 'Inter', sans-serif;
    }
    .q-btn {
        min-height: 60px;
        min-width: 60px;
        font-weight: bold;
    }
    .dashboard-card {
        background: rgba(30, 30, 30, 0.8);
        border: 1px solid #333;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.5);
        padding: 20px;
        backdrop-filter: blur(10px);
    }
    .value-highlight {
        font-size: 2rem;
        font-weight: bold;
        color: #4CAF50;
    }
</style>
""", shared=True)

@ui.page('/')
def index():
    with ui.header().classes('bg-dark text-white items-center q-pa-md shadow-2'):
        ui.label('Industrial HMI - Live Dashboard').classes('text-h5 font-bold')
        ui.space()
        with ui.row().classes('items-center gap-2'):
            global_status = ui.image('/iodd_assets/assets/disconnected.png').classes('w-6 h-6 object-contain')
            ui.label('Modbus Master').classes('text-subtitle1 text-grey')
        ui.space()
        ui.button('Configuration', icon='settings', on_click=lambda: ui.navigate.to('/config')).props('flat')

    # Container for the dynamic cards
    card_container = ui.row().classes('w-full q-pa-md justify-center items-start')

    ui_elements = {}

    def setup_cards():
        card_container.clear()
        ui_elements.clear()
        with card_container:
            for port_str, sensor_type in settings.items():
                if port_str in ["master_type", "master_ip"] or "_" in port_str or not sensor_type:
                    continue
                
                port_num = int(port_str)
                custom_name = settings.get(f"{port_num}_name", "")
                display_title = custom_name if custom_name else f"Port {port_num}"
                
                with ui.card().classes('dashboard-card q-ma-sm w-96 cursor-pointer').on('click', lambda p=port_num: ui.navigate.to(f'/sensor/{p}')):
                    with ui.row().classes('w-full justify-between items-center'):
                        with ui.row().classes('items-center gap-2'):
                            port_status_icon = ui.image('/iodd_assets/assets/disconnected.png').classes('w-4 h-4 object-contain')
                            ui.label(display_title).classes('text-h6 text-primary')
                        ui.label(f"Port {port_num}").classes('text-caption text-grey')
                        
                    pic_path = sensor_parser.get_sensor_pic(sensor_type)
                    icon_path = sensor_parser.get_sensor_icon(sensor_type)
                    img_src = pic_path if pic_path else icon_path
                    
                    if img_src:
                        rel_src = f"/iodd_assets/{os.path.relpath(img_src, os.path.abspath(IODD_DIR))}"
                        with ui.row().classes('w-full justify-center q-mb-md bg-white rounded shadow-sm q-pa-sm'):
                            ui.image(rel_src).classes('h-40 w-full').props('fit="contain"')
                    else:
                        ui.label(sensor_type).classes('text-subtitle1 text-bold q-mb-md text-center w-full')
                    
                    elements = {'port_status_icon': port_status_icon}
                    temp_unit, pres_unit, flow_unit = get_effective_units(port_num)
                    
                    if "MP-F" in sensor_type:
                        with ui.row().classes('w-full justify-between items-center q-mt-sm'):
                            with ui.column().classes('items-center'):
                                elements['temp_unit_lbl'] = ui.label(f"Temp ({temp_unit})").classes('text-caption')
                                elements['temp_knob'] = ui.knob(0, min=-50, max=150, show_value=True).props('color="red" size="60px"')
                            with ui.column().classes('items-center'):
                                elements['pres_unit_lbl'] = ui.label(f"Pres ({pres_unit})").classes('text-caption')
                                elements['pres_knob'] = ui.knob(0, min=0, max=10000, show_value=True).props('color="orange" size="60px"')
                            with ui.column().classes('items-center'):
                                elements['hum_unit_lbl'] = ui.label(f"RH (%)").classes('text-caption')
                                elements['hum_knob'] = ui.knob(0, min=0, max=100, show_value=True).props('color="blue" size="60px"')
                                
                        ui.label("Flow Rate").classes('text-subtitle2 q-mt-md')
                        elements['flow_bar'] = ui.linear_progress(value=0, show_value=False).props('color="blue" size="28px" track-color="dark"')
                        with elements['flow_bar']:
                            elements['flow_lbl'] = ui.label(f"0 {flow_unit}").classes('absolute-center text-white font-bold drop-shadow')
                        
                        with ui.row().classes('w-full justify-between items-center q-mt-sm'):
                            ui.label("Accumulated:").classes('text-caption text-grey')
                            elements['flow_tot_lbl'] = ui.label(f"0 {flow_unit}").classes('text-subtitle1 text-bold')

                    elif "GP-M" in sensor_type:
                        with ui.row().classes('w-full justify-between items-center q-mt-md'):
                            with ui.column().classes('items-center'):
                                elements['pres_unit_lbl'] = ui.label(f"Pressure ({pres_unit})").classes('text-subtitle2')
                                elements['pres_knob'] = ui.knob(0, min=0, max=10000, show_value=True).props('color="orange" size="100px"')
                            with ui.column().classes('items-center'):
                                elements['temp_unit_lbl'] = ui.label(f"Temperature ({temp_unit})").classes('text-subtitle2')
                                elements['temp_knob'] = ui.knob(0, min=-50, max=300, show_value=True).props('color="red" size="100px"')
                    else:
                        elements['generic'] = ui.label("")
                        
                    ui_elements[port_num] = {'sensor_type': sensor_type, 'elements': elements}

    def update_cards():
        if modbus_client.master_online:
            global_status.set_source('/iodd_assets/assets/connected.png')
        else:
            global_status.set_source('/iodd_assets/assets/disconnected.png')
            
        for port_num, card_data in ui_elements.items():
            data = modbus_client.port_data.get(port_num, {})
            port_online = modbus_client.port_status.get(port_num, False)
            sensor_type = card_data['sensor_type']
            elements = card_data['elements']
            
            icon = elements['port_status_icon']
            if port_online:
                icon.set_source('/iodd_assets/assets/connected.png')
            else:
                icon.set_source('/iodd_assets/assets/disconnected.png')
            
            # If not online, maybe freeze or dim? Or just show 0s. Let's just update using whatever was last buffered.
            if not data and not port_online:
                continue
                
            temp_unit, pres_unit, flow_unit = get_effective_units(port_num)
            
            if "MP-F" in sensor_type:
                flow = apply_unit_scaling(data.get('1FlowInst', 0), 'flow', port_num)
                flow_tot = apply_unit_scaling(data.get('1FlowTotal', 0), 'flow_total', port_num)
                pressure = apply_unit_scaling(data.get('1Pressure', 0), 'pres', port_num)
                temp = apply_unit_scaling(data.get('1Temperature', 0) / 10.0, 'temp', port_num)
                hum = data.get('1Humidity', 0) / 10.0
                max_flow = float(settings.get(f"{port_num}_max_flow", 1000.0))
                
                elements['pres_unit_lbl'].set_text(f"Pres ({pres_unit})")
                elements['temp_unit_lbl'].set_text(f"Temp ({temp_unit})")
                
                elements['temp_knob'].value = round(temp, 1)
                elements['pres_knob'].value = round(pressure, 1)
                elements['hum_knob'].value = round(hum, 1)
                
                elements['flow_bar'].value = min(flow / max(max_flow, 1.0), 1.0)
                elements['flow_lbl'].set_text(f"{round(flow, 1)} {flow_unit}")
                elements['flow_tot_lbl'].set_text(f"{round(flow_tot, 1)} {flow_unit}")
                
            elif "GP-M" in sensor_type:
                pressure = apply_unit_scaling(data.get('Pressure', 0), 'pres', port_num)
                temp = apply_unit_scaling(data.get('Temp', 0) / 10.0, 'temp', port_num)
                
                elements['pres_unit_lbl'].set_text(f"Pressure ({pres_unit})")
                elements['temp_unit_lbl'].set_text(f"Temperature ({temp_unit})")
                
                elements['pres_knob'].value = round(pressure, 1)
                elements['temp_knob'].value = round(temp, 1)
            else:
                elements['generic'].set_text(", ".join([f"{k}: {v}" for k, v in data.items()]))

    # Initial build and periodic update
    setup_cards()
    ui.timer(1.0, update_cards)

@ui.page('/sensor/{port_id}')
def sensor_page(port_id: str):
    port_num = int(port_id)
    sensor_type = settings.get(str(port_num), "")
    custom_name = settings.get(f"{port_num}_name", "")
    display_title = custom_name if custom_name else f"Port {port_num}"

    with ui.header().classes('bg-dark text-white items-center q-pa-md shadow-2'):
        ui.button(icon='arrow_back', on_click=lambda: ui.navigate.to('/')).props('flat')
        ui.label(display_title).classes('text-h5 font-bold')
        ui.space()
        with ui.row().classes('items-center gap-2'):
            sensor_status_icon = ui.image('/iodd_assets/assets/disconnected.png').classes('w-6 h-6 object-contain')
            sensor_status_lbl = ui.label('Sensor Disconnected').classes('text-subtitle1 text-grey')

    if not sensor_type:
        with ui.column().classes('w-full items-center q-pa-xl'):
            ui.label("No sensor configured for this port.").classes('text-h5 text-grey q-ma-xl')
        return

    pic_path = sensor_parser.get_sensor_pic(sensor_type)
    icon_path = sensor_parser.get_sensor_icon(sensor_type)
    img_src = pic_path if pic_path else icon_path
    
    with ui.column().classes('w-full items-center q-pa-md'):
        if img_src:
            rel_src = f"/iodd_assets/{os.path.relpath(img_src, os.path.abspath(IODD_DIR))}"
            ui.image(rel_src).classes('h-64 object-contain bg-white rounded shadow-sm q-pa-sm w-full max-w-lg q-mt-md').props('fit="contain"')
        
        # Dashboard display container for this sensor
        data_card = ui.card().classes('dashboard-card w-full max-w-3xl q-mt-lg items-center')
        
        elements = {}
        
        @ui.refreshable
        def render_sensor_data():
            elements.clear()
            temp_unit, pres_unit, flow_unit = get_effective_units(port_num)
            
            if "MP-F" in sensor_type:
                with ui.row().classes('w-full justify-around items-center q-pa-md'):
                    with ui.column().classes('items-center'):
                        ui.label(f"Temperature ({temp_unit})").classes('text-subtitle1 text-grey')
                        elements['temp_knob'] = ui.knob(0, min=-50, max=150, show_value=True).props('color="red" size="120px" track-color="dark"')
                    with ui.column().classes('items-center'):
                        ui.label(f"Pressure ({pres_unit})").classes('text-subtitle1 text-grey')
                        elements['pres_knob'] = ui.knob(0, min=0, max=10000, show_value=True).props('color="orange" size="120px" track-color="dark"')
                    with ui.column().classes('items-center'):
                        ui.label(f"Humidity (%)").classes('text-subtitle1 text-grey')
                        elements['hum_knob'] = ui.knob(0, min=0, max=100, show_value=True).props('color="blue" size="120px" track-color="dark"')

                with ui.row().classes('w-full items-end q-pa-md q-px-xl justify-between flex-nowrap gap-6'):
                    with ui.column().classes('flex-grow'):
                        ui.label(f"Instantaneous Flow Rate ({flow_unit})").classes('text-subtitle1 text-grey')
                        elements['flow_bar'] = ui.linear_progress(value=0, show_value=False).props('color="blue" size="44px" track-color="dark"').classes('q-mt-sm w-full rounded')
                        with elements['flow_bar']:
                            elements['flow_lbl'] = ui.label(f"0 {flow_unit}").classes('absolute-center text-h5 text-white text-bold drop-shadow-lg')
                    with ui.column().classes('items-center shrink-0'):
                        ui.label(f"Max Flowrate").classes('text-subtitle1 text-grey')
                        max_f = ui.number(value=float(settings.get(f"{port_num}_max_flow", 1000.0)), step=10, on_change=lambda e: [settings.update({f"{port_num}_max_flow": e.value}), save_settings()]).classes('w-28 q-mt-sm')
                        
                with ui.row().classes('w-full justify-center items-center q-pa-sm'):
                    ui.label("Accumulated Flow:").classes('text-h6 text-grey q-mr-md')
                    elements['flow_tot_lbl'] = ui.label(f"0 {flow_unit}").classes('text-h5 text-bold')

                with ui.row().classes('w-full justify-center items-center q-pa-sm q-mt-sm gap-4'):
                    ui.label("Valve State:").classes('text-h6 text-grey font-bold')
                    ValveToggle(port_num, initial_state=False, client=modbus_client)

            elif "GP-M" in sensor_type:
                with ui.row().classes('w-full justify-around items-center q-pa-md'):
                    with ui.column().classes('items-center'):
                        ui.label(f"Pressure ({pres_unit})").classes('text-subtitle1 text-grey')
                        elements['pres_knob'] = ui.knob(0, min=-50, max=10000, show_value=True).props('color="orange" size="150px" track-color="dark"')
                    with ui.column().classes('items-center'):
                        ui.label(f"Temperature ({temp_unit})").classes('text-subtitle1 text-grey')
                        elements['temp_knob'] = ui.knob(0, min=-50, max=300, show_value=True).props('color="red" size="150px" track-color="dark"')
            else:
                elements['generic'] = ui.label("")
                
        with data_card:
            render_sensor_data()
            
        def update_single_card():
            data = modbus_client.port_data.get(port_num, {})
            port_online = modbus_client.port_status.get(port_num, False)
            
            if port_online:
                sensor_status_icon.set_source('/iodd_assets/assets/connected.png')
                sensor_status_lbl.set_text('Sensor Connected')
                sensor_status_lbl.classes(replace='text-grey', add='text-green')
            else:
                sensor_status_icon.set_source('/iodd_assets/assets/disconnected.png')
                sensor_status_lbl.set_text('Sensor Disconnected')
                sensor_status_lbl.classes(replace='text-green', add='text-grey')
                
            if not data and not port_online:
                return
            
            temp_unit, pres_unit, flow_unit = get_effective_units(port_num)
            
            if "MP-F" in sensor_type:
                flow = apply_unit_scaling(data.get('1FlowInst', 0), 'flow', port_num)
                flow_tot = apply_unit_scaling(data.get('1FlowTotal', 0), 'flow_total', port_num)
                pressure = apply_unit_scaling(data.get('1Pressure', 0), 'pres', port_num)
                temp = apply_unit_scaling(data.get('1Temperature', 0) / 10.0, 'temp', port_num)
                hum = data.get('1Humidity', 0) / 10.0
                max_flow = float(settings.get(f"{port_num}_max_flow", 1000.0))
                
                elements.get('temp_knob', ui.knob()).value = round(temp, 1)
                elements.get('pres_knob', ui.knob()).value = round(pressure, 1)
                elements.get('hum_knob', ui.knob()).value = round(hum, 1)
                
                elements.get('flow_bar', ui.linear_progress()).value = min(flow / max(max_flow, 1.0), 1.0)
                elements.get('flow_lbl', ui.label()).set_text(f"{round(flow, 1)} {flow_unit}")
                elements.get('flow_tot_lbl', ui.label()).set_text(f"{round(flow_tot, 1)} {flow_unit}")
            elif "GP-M" in sensor_type:
                pressure = apply_unit_scaling(data.get('Pressure', 0), 'pres', port_num)
                temp = apply_unit_scaling(data.get('Temp', 0) / 10.0, 'temp', port_num)
                
                elements.get('pres_knob', ui.knob()).value = round(pressure, 1)
                elements.get('temp_knob', ui.knob()).value = round(temp, 1)
            else:
                elements.get('generic', ui.label()).set_text(", ".join([f"{k}: {v}" for k, v in data.items()]))

        ui.timer(1.0, update_single_card)
        
        # Override Settings Card
        with ui.card().classes('dashboard-card w-full max-w-3xl q-mt-lg'):
            ui.label("Unit Selection & Scaling").classes('text-h6 text-primary q-mb-md')
            
            override_cb = ui.checkbox("Override Global Units").bind_value(settings, f"{port_num}_override_units")
            override_cb.on('update:model-value', lambda: [save_settings(), render_sensor_data.refresh()])
            
            with ui.row().classes('items-center gap-6 q-mt-sm q-ml-md').bind_visibility_from(override_cb, 'value'):
                temp_u = ui.select(['°C', '°F'], label="Display Temp Unit").classes('w-32')
                temp_u.bind_value(settings, f"{port_num}_temp_unit")
                temp_u.on('update:model-value', lambda: [save_settings(), render_sensor_data.refresh()])
                
                pres_u = ui.select(['kPa', 'MPa', 'psi', 'bar'], label="Display Pres Unit").classes('w-32')
                pres_u.bind_value(settings, f"{port_num}_pres_unit")
                pres_u.on('update:model-value', lambda: [save_settings(), render_sensor_data.refresh()])
                
                flow_u = ui.select(['L/min', 'CFM'], label="Display Flow Unit").classes('w-32')
                flow_u.bind_value(settings, f"{port_num}_flow_unit")
                flow_u.on('update:model-value', lambda: [save_settings(), render_sensor_data.refresh()])

            ui.separator().classes('q-my-md')
            
            rescale_cb = ui.checkbox("Rescale Output (Apply Math Conversion)").bind_value(settings, f"{port_num}_rescale")
            rescale_cb.on('update:model-value', lambda: [save_settings(), render_sensor_data.refresh()])
            
            with ui.row().classes('items-center gap-6 q-mt-sm q-ml-md').bind_visibility_from(rescale_cb, 'value'):
                scale_temp_f = ui.select(['°C', '°F'], label="Scale TEMP From").classes('w-40')
                scale_temp_f.bind_value(settings, f"{port_num}_scale_from_temp")
                scale_temp_f.on('update:model-value', lambda: [save_settings(), render_sensor_data.refresh()])
                
                scale_pres_f = ui.select(['kPa', 'MPa', 'psi', 'bar'], label="Scale PRES From").classes('w-40')
                scale_pres_f.bind_value(settings, f"{port_num}_scale_from_pres")
                scale_pres_f.on('update:model-value', lambda: [save_settings(), render_sensor_data.refresh()])

                scale_flow_f = ui.select(['L/min', 'CFM'], label="Scale FLOW From").classes('w-40')
                scale_flow_f.bind_value(settings, f"{port_num}_scale_from_flow")
                scale_flow_f.on('update:model-value', lambda: [save_settings(), render_sensor_data.refresh()])
                
                scale_flow_t_f = ui.select(['L', 'ft³', 'gal'], label="Scale TOTAL FLOW From").classes('w-40')
                scale_flow_t_f.bind_value(settings, f"{port_num}_scale_from_flow_total")
                scale_flow_t_f.on('update:model-value', lambda: [save_settings(), render_sensor_data.refresh()])

@ui.page('/config')
def config_page():
    with ui.header().classes('bg-dark text-white items-center q-pa-md shadow-2'):
        ui.button(icon='arrow_back', on_click=lambda: ui.navigate.to('/')).props('flat')
        ui.label('Configuration').classes('text-h5 font-bold')
        ui.space()
        ui.button('Save', icon='save', on_click=save_settings).props('color="primary"')

    available_sensors = [""] + sensor_parser.get_available_sensors()

    with ui.row().classes('w-full q-pa-md justify-center'):
        with ui.column().classes('w-1/2 dashboard-card'):
            with ui.row().classes('w-full justify-between items-center'):
                ui.label("Master Configuration").classes('text-h6')
                
                async def handle_discover():
                    try:
                        max_ports = 8 if "8" in settings.get("master_type", "NQ-MP8L") else 4
                        discovered = await modbus_client.auto_discover(max_ports=max_ports)
                        if discovered:
                            for p, sensor in discovered.items():
                                settings[str(p)] = sensor
                            save_settings()
                            port_mapping_ui.refresh()
                            ui.notify("Sensors Auto-Discovered!", type="positive", icon="search")
                        else:
                            ui.notify("No sensors found or mapped.", type="warning")
                    except Exception as e:
                        ui.notify(f"Discovery Error: {e}", type="negative")

                ui.button("Auto Discover", icon="search", on_click=handle_discover, color="amber-8").classes('rounded shadow')
            
            @ui.refreshable
            def port_mapping_ui():
                master_type = settings.get("master_type", "NQ-MP8L (8 Ports)")
                num_ports = 8 if "8" in master_type else 4
                
                for i in range(1, num_ports + 1):
                    with ui.row().classes('w-full items-center justify-between q-my-sm'):
                        with ui.column().classes('gap-0'):
                            ui.label(f"Port {i}").classes('text-bold')
                            ui.label(f"Reg {1000 + (i-1)*50}").classes('text-caption text-grey')
                        
                        name_input = ui.input(placeholder="Sensor Name").classes('w-32')
                        name_input.bind_value(settings, f"{i}_name")

                        def get_icon_src(pid):
                            ic = sensor_parser.get_sensor_icon(pid)
                            if ic:
                                return f"/iodd_assets/{os.path.relpath(ic, os.path.abspath(IODD_DIR))}"
                            return ""

                        with ui.row().classes('items-center gap-4'):
                            img = ui.image().classes('w-12 h-12 object-contain bg-white rounded shadow-sm')
                            img.bind_source_from(settings, str(i), backward=get_icon_src)
                            img.bind_visibility_from(settings, str(i), backward=lambda pid: bool(get_icon_src(pid)))
                            
                            select = ui.select(available_sensors, value=settings.get(str(i), ""), label="Sensor Type").classes('w-48')
                            select.bind_value(settings, str(i))

            with ui.row().classes('w-full items-center justify-between'):
                ip_label = ui.label()
                ip_label.bind_text_from(settings, 'master_ip', backward=lambda ip: f"Current Master IP: {ip if ip else '127.0.0.1'}")
                
                async def scan_for_master():
                    ui.notify("Scanning network for IO-Link Masters...")
                    devices = await modbus_client.scan_network()
                    if devices:
                        settings["master_ip"] = devices[0]
                        # In a real app we would probe the master model via Modbus register here
                        settings["master_type"] = "NQ-MP8L (8 Ports)" if "8" in devices[0] else "NQ-MP8L (8 Ports)"
                        ui.notify(f"Found Master at {devices[0]}")
                        port_mapping_ui.refresh()
                    else:
                        ui.notify("No masters found on port 502.")

                def prompt_manual_ip():
                    with ui.dialog() as dialog, ui.card():
                        ui.label("Enter Master IP Address")
                        ip_input = ui.input(value=settings.get("master_ip", "192.168.1.100"))
                        
                        def set_ip():
                            settings["master_ip"] = ip_input.value
                            ui.notify(f"IP Set to {ip_input.value}")
                            dialog.close()
                            port_mapping_ui.refresh()
                        
                        ui.button("Save", on_click=set_ip)
                    dialog.open()

                with ui.row():
                    ui.button(icon='search', on_click=scan_for_master).props('flat round')
                    ui.button(icon='edit', on_click=prompt_manual_ip).props('flat round')

            master_options = ["NQ-MP8L (8 Ports)", "NQ-EP4L (4 Ports)"]
            
            def get_master_icon(mtype):
                if not mtype:
                    return ""
                if "NQ-EP4L" in mtype:
                    return "/iodd_assets/extracted_NQ-EP4L_EDS_208/NQ-EP4L_EDS_208/Keyence_NQEP4L.ico"
                if "NQ-MP8L" in mtype:
                    return "/iodd_assets/extracted_NQ-MP8L_EDS_208/NQ-MP8L_EDS_208/Keyence_NQMP8L.ico"
                return ""

            with ui.row().classes('items-center gap-4'):
                master_img = ui.image().classes('w-12 h-12 object-contain bg-white rounded shadow-sm')
                master_img.bind_source_from(settings, "master_type", backward=get_master_icon)
                
                master_select = ui.select(master_options, value=settings.get("master_type", "NQ-MP8L (8 Ports)"), label="Master Type", on_change=port_mapping_ui.refresh)
                master_select.bind_value(settings, "master_type")
                
            with ui.row().classes('items-center gap-4 q-mt-sm'):
                temp_u = ui.select(['°C', '°F'], value=settings.get("global_temp_unit", "°C"), label="Global Temp Unit", on_change=port_mapping_ui.refresh).classes('w-32')
                temp_u.bind_value(settings, "global_temp_unit")
                
                pres_u = ui.select(['kPa', 'MPa', 'psi', 'bar'], value=settings.get("global_pres_unit", "kPa"), label="Global Pres Unit", on_change=port_mapping_ui.refresh).classes('w-32')
                pres_u.bind_value(settings, "global_pres_unit")
                
                flow_u = ui.select(['L/min', 'CFM'], value=settings.get("global_flow_unit", "L/min"), label="Global Flow Unit", on_change=port_mapping_ui.refresh).classes('w-32')
                flow_u.bind_value(settings, "global_flow_unit")
            
            ui.separator().classes('q-my-md')
            port_mapping_ui()
            
        with ui.column().classes('w-1/3 q-ml-md dashboard-card items-center'):
            ui.label("System Tools").classes('text-h6')
            
            async def handle_upload(e):
                # Basic upload handler
                os.makedirs(IODD_DIR, exist_ok=True)
                file_path = os.path.join(IODD_DIR, e.name)
                with open(file_path, 'wb') as f:
                    f.write(e.content.read())
                ui.notify(f"Uploaded {e.name}")
                sensor_parser._extract_all()
                sensor_parser._parse_all()
                # Reload page to refresh select options
                ui.navigate.to('/config')

            ui.upload(on_upload=handle_upload, label="Upload IODD Zip").classes('w-full max-w-sm')
            ui.separator().classes('w-full q-my-md')
            ui.label("Remote Access").classes('text-subtitle1')
            # Mock QR code for now
            ui.html('<img src="https://api.qrserver.com/v1/create-qr-code/?size=150x150&data=http://local_ip:8080" />')



# Run the Modbus polling in the background when the app starts
app.on_startup(lambda: asyncio.create_task(modbus_client.poll_ports(settings, sensor_parser)))

if __name__ in {"__main__", "__mp_main__"}:
    ui.run(port=8080, dark=True, title="Industrial HMI")
