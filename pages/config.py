from nicegui import ui
import os
from shared_state import settings, save_settings, modbus_client, sensor_parser, IODD_DIR, data_logger
from components import SimulationToggle, HostNetworkToggle

@ui.page('/config')
def config_page():
    with ui.header().classes('bg-dark text-white items-center q-pa-md shadow-2'):
        ui.button(icon='arrow_back', on_click=lambda: ui.navigate.to('/')).props('flat')
        ui.label('Configuration').classes('text-h5 font-bold')
        ui.space()
        ui.button('Save', icon='save', on_click=save_settings).props('color="primary"')

    available_sensors = [""] + sensor_parser.get_available_sensors()

    with ui.row().classes('w-full q-pa-md justify-center flex-col md:flex-row md:items-start gap-4 flex-nowrap'):
        with ui.column().classes('w-full md:w-1/2 dashboard-card text-center md:text-left'):
            with ui.row().classes('w-full justify-between items-center'):
                ui.label("IO Link Master Configuration").classes('text-h6')
            
            @ui.refreshable
            def port_mapping_ui():
                master_type = settings.get("master_type", "NQ-MP8L (8 Ports)")
                num_ports = 8 if "8" in master_type else 4
                
                for i in range(1, num_ports + 1):
                    def get_icon_src(pid):
                        ic = sensor_parser.get_sensor_icon(pid)
                        if ic:
                            return f"/iodd_assets/{os.path.relpath(ic, os.path.abspath(IODD_DIR))}"
                        return ""

                    # We pass the loop variable through default arg to capture it
                    def on_setting_change(e, port_num=i):
                        save_settings()
                        port_mapping_ui.refresh()

                    with ui.expansion().classes('w-full bg-dark rounded q-my-sm shadow-2') as exp:
                        with exp.add_slot('header'):
                            with ui.row().classes('w-full items-center justify-between no-wrap'):
                                with ui.row().classes('items-center gap-4'):
                                    ui.label(f"Port {i}").classes('text-bold text-h6 w-16')
                                    
                                    img = ui.image().classes('w-10 h-10 object-contain bg-white rounded shadow-sm')
                                    img.bind_source_from(settings, str(i), backward=get_icon_src)
                                    img.bind_visibility_from(settings, str(i), backward=lambda pid: bool(get_icon_src(pid)))
                                    
                                    sensor_type_label = ui.label().classes('text-subtitle1 text-grey-4')
                                    sensor_type_label.bind_text_from(settings, str(i), backward=lambda type_str: type_str if type_str else "Empty")
                                
                                name_label = ui.label().classes('text-subtitle1 font-bold')
                                name_label.bind_text_from(settings, f"{i}_name")

                        with ui.column().classes('w-full q-pa-md q-gutter-md'):
                            with ui.row().classes('w-full items-center gap-4'):
                                select = ui.select(available_sensors, value=settings.get(str(i), ""), label="Sensor Type").classes('w-64')
                                select.bind_value(settings, str(i))
                                select.on('update:model-value', on_setting_change)
                                
                                name_input = ui.input(label="Sensor Name", placeholder="e.g. Main Line Air").classes('w-64')
                                name_input.bind_value(settings, f"{i}_name")
                                # Explicitly bind to 'blur' or 'keyup.enter' to save without refreshing on every stroke
                                name_input.on('blur', save_settings)
                                name_input.on('keyup.enter', save_settings)

                            with ui.row().classes('w-full items-center gap-4'):
                                addr_input = ui.number(label="Modbus Address", value=settings.get(f"{i}_modbus_address", (i-1)*50), format="%d", on_change=save_settings).classes('w-32')
                                addr_input.bind_value(settings, f"{i}_modbus_address")
                                
                                len_input = ui.number(label="Modbus Length", value=settings.get(f"{i}_modbus_length", 50), format="%d", on_change=save_settings).classes('w-32')
                                len_input.bind_value(settings, f"{i}_modbus_length")

                            def detect_native_units(pid):
                                units = {"pres": None, "flow": None, "temp": None}
                                if not pid: return units
                                smap = sensor_parser.get_sensor_map(pid)
                                for var in smap.values():
                                    u = var.get("native_unit")
                                    name = var.get("display_name", "").lower()
                                    if u:
                                        if "pressure" in name: units["pres"] = u
                                        elif "flow" in name: units["flow"] = u
                                        elif "temp" in name: units["temp"] = u
                                return units

                            with ui.row().classes('w-full items-center gap-4'):
                                rescale_check = ui.checkbox("Enable Unit Rescaling").bind_value(settings, f"{i}_rescale").on('update:model-value', on_setting_change)
                                
                                native = detect_native_units(settings.get(str(i)))
                                
                                with ui.row().classes('gap-2').bind_visibility_from(settings, f"{i}_rescale"):
                                    def setup_unit_select(label, key, native_unit):
                                        current = settings.get(key)
                                        if not current and native_unit:
                                            settings[key] = native_unit
                                        
                                        s = ui.select(['kPa', 'MPa', 'psi', 'bar', 'L/min', 'CFM', '°C', '°F'], label=label).classes('w-32')
                                        s.bind_value(settings, key).on('update:model-value', save_settings)
                                        if native_unit:
                                            s.props(f'suffix="({native_unit})"')
                                            s.tooltip(f"Auto-detected native unit: {native_unit}")
                                        return s

                                    setup_unit_select("Scale From (Pres)", f"{i}_scale_from_pres", native["pres"])
                                    setup_unit_select("Scale From (Flow)", f"{i}_scale_from_flow", native["flow"])
                                    setup_unit_select("Scale From (Temp)", f"{i}_scale_from_temp", native["temp"])

            ui.separator().classes('w-full q-my-md')

            with ui.row().classes('w-full items-center justify-between q-mb-md q-pa-md bg-black/30 rounded border border-gray-700'):
                with ui.column().classes('gap-1'):
                    ui.label("Host IO-Link Master via Local Connection").classes('text-lg font-bold')
                    ui.label("Configures eth0 as a DHCP server temporarily.").classes('text-sm text-grey-4')
                    
                    with ui.row().classes('items-center gap-2 q-mt-sm'):
                        ui.label("Host IP Address:").classes('text-subtitle2 font-bold')
                        host_ip_input = ui.input(value=settings.get("host_ip", "172.16.1.1")).classes('w-32')
                        host_ip_input.props('dense outlined')
                        def update_host_ip(e):
                            settings["host_ip"] = e.value
                            save_settings()
                        host_ip_input.on('blur', lambda e: update_host_ip(host_ip_input))
                        host_ip_input.on('keyup.enter', lambda e: update_host_ip(host_ip_input))

                async def toggle_local_host(state):
                    import asyncio
                    settings["host_local_network"] = state
                    save_settings()
                    ip_to_use = settings.get("host_ip", "172.16.1.1")
                    
                    host_toggle.set_processing(True)
                    try:
                        if state:
                            ui.notify(f"Configuring eth0 as DHCP Server ({ip_to_use})...", type="info", timeout=3000)
                            process = await asyncio.create_subprocess_exec("sudo", "bash", "scripts/enable_local_host.sh", ip_to_use)
                            await process.communicate()
                            if process.returncode == 0:
                                ui.notify("eth0 configured successfully.", type="positive")
                            else:
                                ui.notify(f"Failed to configure eth0: process returned {process.returncode}", type="negative")
                        else:
                            ui.notify("Reverting eth0 to automatic DHCP client...", type="info", timeout=3000)
                            process = await asyncio.create_subprocess_exec("sudo", "bash", "scripts/disable_local_host.sh")
                            await process.communicate()
                            if process.returncode == 0:
                                ui.notify("eth0 reverted successfully.", type="positive")
                            else:
                                ui.notify(f"Failed to revert eth0: process returned {process.returncode}", type="negative")
                    except Exception as err:
                        ui.notify(f"Error changing network state: {err}", type="negative")
                    finally:
                        host_toggle.set_processing(False)

                host_toggle = HostNetworkToggle(initial_state=settings.get("host_local_network", False), on_change=toggle_local_host)

            with ui.row().classes('w-full items-center justify-between'):
                ip_label = ui.label()
                ip_label.bind_text_from(settings, 'master_ip', backward=lambda ip: f"Current Master IP: {ip if ip else '127.0.0.1'}")
                
                def get_network_interfaces():
                    import subprocess
                    interfaces = []
                    try:
                        output = subprocess.check_output("ip -o addr show", shell=True).decode()
                        for line in output.split("\n"):
                            if not line: continue
                            parts = line.split()
                            if len(parts) >= 4 and parts[2] == "inet":
                                interfaces.append({"iface": parts[1], "ip": parts[3]})
                    except Exception:
                        pass
                    if not interfaces:
                        interfaces.append({"iface": "localhost", "ip": "127.0.0.1/8"})
                    return interfaces

                def prompt_scan_network():
                    interfaces = get_network_interfaces()
                    options = {iface['ip']: f"{iface['iface']} ({iface['ip']})" for iface in interfaces}
                    
                    with ui.dialog() as dialog, ui.card().classes('w-96'):
                        ui.label("Select Network Interface to Scan").classes('text-h6 font-bold q-mb-md')
                        selected_iface = ui.select(options, value=list(options.keys())[0], label="Interface").classes('w-full q-mb-md')
                        
                        async def perform_scan():
                            dialog.close()
                            subnet = selected_iface.value
                            ui.notify(f"Scanning {subnet} for IO-Link Masters...", type="info")
                            
                            import ipaddress
                            try:
                                net = ipaddress.IPv4Network(subnet, strict=False)
                                broadcast_ip = str(net.broadcast_address)
                            except Exception:
                                broadcast_ip = "255.255.255.255"
                                
                            devices = await modbus_client.scan_cip_network(broadcast_ip=broadcast_ip)
                            if devices:
                                dev = devices[0]
                                settings["master_ip"] = dev["ip"]
                                
                                num_ports = 8
                                if "NQ-EP4" in dev["product_name"]:
                                    settings["master_type"] = "NQ-EP4L (4 Ports)"
                                    num_ports = 4
                                elif "NQ-MP8" in dev["product_name"]:
                                    settings["master_type"] = "NQ-MP8L (8 Ports)"
                                    num_ports = 8
                                else:
                                    settings["master_type"] = "NQ-MP8L (8 Ports)"
                                    
                                ui.notify(f"Found {dev['product_name']} at {dev['ip']}. Querying ports...", type="info")
                                
                                # Query the master for connected sensors
                                discovered_sensors = await modbus_client.discover_connected_sensors(dev["ip"], num_ports=num_ports)
                                
                                sensors_mapped = 0
                                available = sensor_parser.get_available_sensors()
                                for port, info in discovered_sensors.items():
                                    prod_id_str = info.get("product_id_str")
                                    vid = info.get("vendor_id")
                                    did = info.get("device_id")
                                    
                                    mapped_id = None
                                    if prod_id_str and prod_id_str in available:
                                        mapped_id = prod_id_str
                                    else:
                                        mapped_id = sensor_parser.get_product_by_id(vid, did)
                                        
                                    if mapped_id:
                                        settings[str(port)] = mapped_id
                                        sensors_mapped += 1
                                
                                ui.notify(f"Discovery complete. Auto-mapped {sensors_mapped} sensors.", type="positive")
                                save_settings()
                                port_mapping_ui.refresh()
                            else:
                                ui.notify("No masters found via auto-discovery.", type="warning")
                        
                        with ui.row().classes('w-full justify-end q-mt-md gap-4'):
                            ui.button("Cancel", on_click=dialog.close).props('flat')
                            ui.button("Scan", on_click=perform_scan).props('color="primary"')
                            
                    dialog.open()

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
                    ui.button(icon='search', on_click=prompt_scan_network).props('flat round')
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
                
            with ui.row().classes('items-center gap-6 q-mt-md'):
                ui.label("Endianness (Swaps):").classes('text-grey-4 text-sm')
                ui.checkbox("Byte Swap").bind_value(settings, "byte_swap").on('update:model-value', save_settings).props('dense')
                ui.checkbox("Word Swap").bind_value(settings, "word_swap").on('update:model-value', save_settings).props('dense')
            
            ui.separator().classes('q-my-md')
            port_mapping_ui()
            
        with ui.column().classes('w-full md:w-1/3 dashboard-card items-center'):
            ui.label("System Settings").classes('text-h6')

            with ui.expansion('Dashboard Slot Mapping', icon='dashboard').classes('w-full bg-dark rounded q-my-sm'):
                ui.label("Manually assign physical ports to dashboard locations:").classes('text-xs text-grey-4 mb-2')
                
                port_options = {"Auto": "Auto Tracking"}
                for p_idx in range(1, 9):
                    port_options[str(p_idx)] = f"Port {p_idx}"
                
                slots = [
                    ("slot_gp1", "Wet Air (GP-M)"),
                    ("slot_gp2", "Dry Air (GP-M)"),
                    ("slot_mp1", "Outlet 1 (MP-F)"),
                    ("slot_mp2", "Outlet 2 (MP-F)"),
                    ("slot_mp3", "Outlet 3 (MP-F)"),
                ]
                
                for key, label in slots:
                    ui.select(port_options, value=settings.get(key, "Auto"), label=label).classes('w-full').bind_value(settings, key).on('update:model-value', save_settings)

            with ui.expansion('Data Logging Settings', icon='save').classes('w-full bg-dark rounded q-my-sm'):
                ui.checkbox("Enable Local Logging").bind_value(settings, "enable_logging").on('update:model-value', save_settings)
                ui.number("Logging Interval (s)", value=10.0, format="%.1f").bind_value(settings, "logging_interval").on('update:model-value', save_settings)
                ui.number("Data Retention (days)", value=7.0, format="%.1f").bind_value(settings, "data_retention_days").on('update:model-value', save_settings)

                def confirm_reset():
                    with ui.dialog() as dialog, ui.card():
                        ui.label("Are you sure you want to delete all historical sensor data? This cannot be undone.").classes('text-red font-bold q-mb-md')
                        with ui.row().classes('w-full justify-end q-mt-md gap-4'):
                            ui.button("Cancel", on_click=dialog.close).props('flat')
                            def do_reset():
                                if data_logger.clear_database():
                                    ui.notify("Database cleared successfully.", type="positive")
                                else:
                                    ui.notify("Failed to clear database.", type="negative")
                                dialog.close()
                            ui.button("Reset Database", color='red', on_click=do_reset)
                    dialog.open()
                
                ui.button("Reset Database", color='red', icon='delete_forever', on_click=confirm_reset).classes('q-mt-md')

            with ui.expansion('OPC-UA Compressor Settings', icon='settings_input_component').classes('w-full bg-dark rounded q-my-sm'):
                ui.input(label="OPC-UA Server IP").classes('w-full').bind_value(settings, "opcua_ip").on('update:model-value', save_settings)
                ui.input(label="Pressure Node ID").classes('w-full').bind_value(settings, "opcua_node_pressure").on('update:model-value', save_settings)
                ui.input(label="Temp Node ID").classes('w-full').bind_value(settings, "opcua_node_temp").on('update:model-value', save_settings)
                ui.input(label="Hours Node ID").classes('w-full').bind_value(settings, "opcua_node_hours").on('update:model-value', save_settings)
                ui.input(label="State Node ID").classes('w-full').bind_value(settings, "opcua_node_state").on('update:model-value', save_settings)
                ui.input(label="Start Node ID").classes('w-full').bind_value(settings, "opcua_node_start").on('update:model-value', save_settings)
                ui.input(label="Stop Node ID").classes('w-full').bind_value(settings, "opcua_node_stop").on('update:model-value', save_settings)

            with ui.expansion('Raw Data Diagnostic', icon='query_stats').classes('w-full bg-dark rounded q-my-sm'):
                ui.label("Latest raw registers (Hex):").classes('text-xs text-grey-4 mb-2')
                
                # Update loop for raw data
                raw_labels = {}
                for p_idx in range(1, 9):
                    with ui.row().classes('w-full items-center gap-2 no-wrap'):
                        ui.label(f"P{p_idx}:").classes('text-bold w-6 text-xs')
                        raw_labels[p_idx] = ui.label("[]").classes('font-mono text-xs truncate flex-1 overflow-hidden')
                
                def update_diagnostics():
                    for p_idx, label in raw_labels.items():
                        regs = modbus_client.port_raw_data.get(p_idx, [])
                        if regs:
                            label.text = " ".join([f"{r:04X}" for r in regs[:6]]) + ("..." if len(regs) > 6 else "")
                        else:
                            label.text = "No data"
                
                ui.timer(1.0, update_diagnostics)

            ui.label("Simulation Mode").classes('text-subtitle1 q-mt-sm font-bold text-grey')
            SimulationToggle(initial_state=settings.get("use_simulation", False))
            ui.separator().classes('w-full q-my-md')
            
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
            ui.label("Remote Access").classes('text-h6')
            
            # Use the existing get_network_interfaces to find the actual IP
            interfaces = get_network_interfaces()
            
            wlan_iface = next((i for i in interfaces if "wlan" in i["iface"]), None)
            default_ip = "127.0.0.1"
            
            if wlan_iface:
                default_ip = wlan_iface["ip"].split("/")[0]
            else:
                for iface in interfaces:
                    if iface["ip"].startswith("127."):
                        continue
                    default_ip = iface["ip"].split("/")[0]
                    break

            # Deduplicate by interface name and ip
            ip_options = {}
            for iface in interfaces:
                ip_addr = iface["ip"].split("/")[0]
                ip_options[ip_addr] = f'{iface["iface"]} ({ip_addr})'
                
            remote_ip = ui.select(ip_options, value=default_ip, label="Select Network Interface").classes('w-full')

            @ui.refreshable
            def render_qr():
                current_ip = remote_ip.value
                ui.html(f'<img src="https://api.qrserver.com/v1/create-qr-code/?size=150x150&data=http://{current_ip}:8080" />', sanitize=False)
                ui.label(f"http://{current_ip}:8080").classes('text-subtitle1 text-grey font-mono q-mt-sm')

            remote_ip.on('update:model-value', render_qr.refresh)
            # Render initially
            render_qr()
