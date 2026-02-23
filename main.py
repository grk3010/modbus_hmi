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
                
                with ui.card().classes('dashboard-card q-ma-sm w-96'):
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
                    temp_unit = settings.get("global_temp_unit", "°C")
                    pres_unit = settings.get("global_pres_unit", "kPa")
                    
                    if "MP-F" in sensor_type:
                        ui.label("Flow Rate").classes('text-subtitle2')
                        elements['flow_bar'] = ui.linear_progress(value=0, show_value=False).props('color="blue" size="20px"')
                        elements['flow_lbl'] = ui.label("0 L/min").classes('value-highlight text-blue')
                        
                        with ui.row().classes('w-full justify-between q-mt-md'):
                            with ui.column():
                                ui.label(f"Pressure ({pres_unit})").classes('text-caption')
                                elements['pres_lbl'] = ui.label(f"0 {pres_unit}").classes('text-h6')
                            with ui.column():
                                ui.label(f"Temperature ({temp_unit})").classes('text-caption')
                                elements['temp_lbl'] = ui.label(f"0 {temp_unit}").classes('text-h6')

                    elif "GP-M" in sensor_type:
                        with ui.row().classes('w-full justify-between items-center q-mt-md'):
                            with ui.column().classes('items-center'):
                                ui.label(f"Pressure ({pres_unit})").classes('text-subtitle2')
                                elements['pres_knob'] = ui.knob(0, min=0, max=10000, show_value=True).props('color="orange" size="100px"')
                            with ui.column().classes('items-center'):
                                ui.label(f"Temperature ({temp_unit})").classes('text-subtitle2')
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
                
            temp_unit = settings.get("global_temp_unit", "°C")
            pres_unit = settings.get("global_pres_unit", "kPa")
            
            if "MP-F" in sensor_type:
                flow = data.get('1FlowInst', 0)
                pressure = data.get('1Pressure', 0)
                temp = data.get('1Temperature', 0)
                
                elements['flow_bar'].value = min(flow / 1000.0, 1.0)
                elements['flow_lbl'].set_text(f"{flow} L/min")
                elements['pres_lbl'].set_text(f"{pressure} {pres_unit}")
                elements['temp_lbl'].set_text(f"{temp / 10.0} {temp_unit}")
            elif "GP-M" in sensor_type:
                pressure = data.get('Pressure', 0)
                temp = data.get('Temp', 0)
                
                elements['pres_knob'].value = pressure
                elements['temp_knob'].value = temp / 10.0
            else:
                elements['generic'].set_text(", ".join([f"{k}: {v}" for k, v in data.items()]))

    # Initial build and periodic update
    setup_cards()
    ui.timer(1.0, update_cards)

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
            ui.label("Master Configuration").classes('text-h6')
            
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
