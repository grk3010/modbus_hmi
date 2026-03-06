import os
from nicegui import ui
from shared_state import settings, modbus_client, sensor_parser, IODD_DIR, get_effective_units, apply_unit_scaling, save_settings
from components import ValveToggle

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
                        elements['temp_knob'] = ui.knob(0, min=-50, max=150, show_value=True).props('color="red" size="120px" track-color="dark" readonly disable')
                    with ui.column().classes('items-center'):
                        ui.label(f"Pressure ({pres_unit})").classes('text-subtitle1 text-grey')
                        elements['pres_knob'] = ui.knob(0, min=0, max=10000, show_value=True).props('color="orange" size="120px" track-color="dark" readonly disable')
                    with ui.column().classes('items-center'):
                        ui.label(f"Humidity (%)").classes('text-subtitle1 text-grey')
                        elements['hum_knob'] = ui.knob(0, min=0, max=100, show_value=True).props('color="blue" size="120px" track-color="dark" readonly disable')

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
                    elements['valve_toggle'] = ValveToggle(port_num, initial_state=False, client=modbus_client)

            elif "GP-M" in sensor_type:
                with ui.row().classes('w-full justify-around items-center q-pa-md'):
                    with ui.column().classes('items-center'):
                        ui.label(f"Pressure ({pres_unit})").classes('text-subtitle1 text-grey')
                        elements['pres_knob'] = ui.knob(0, min=-50, max=10000, show_value=True).props('color="orange" size="150px" track-color="dark" readonly disable')
                    with ui.column().classes('items-center'):
                        ui.label(f"Temperature ({temp_unit})").classes('text-subtitle1 text-grey')
                        elements['temp_knob'] = ui.knob(0, min=-50, max=300, show_value=True).props('color="red" size="150px" track-color="dark" readonly disable')
            else:
                elements['generic'] = ui.label("")
                
        with data_card:
            render_sensor_data()
            
        def update_single_card():
            data = modbus_client.port_data.get(port_num, {})
            port_online = modbus_client.port_status.get(port_num, False)
            
            is_simulating = settings.get("use_simulation", False)
            if is_simulating:
                import random
                if "MP-F" in sensor_type:
                    data = {
                        '1FlowInst': random.uniform(10, 500) * 10,
                        '1FlowTotal': random.uniform(100, 5000),
                        '1Pressure': random.uniform(50, 800),
                        '1Temperature': random.uniform(200, 800),
                        '1Humidity': random.uniform(300, 700)
                    }
                elif "GP-M" in sensor_type:
                    data = {
                        'Pressure': random.uniform(0, 5000),
                        'Temp': random.uniform(200, 800)
                    }

            if port_online:
                sensor_status_icon.set_source('/iodd_assets/assets/connected.png')
                sensor_status_lbl.set_text('Sensor Connected')
                sensor_status_lbl.classes(replace='text-grey', add='text-green')
            else:
                sensor_status_icon.set_source('/iodd_assets/assets/disconnected.png')
                sensor_status_lbl.set_text('Sensor Disconnected (Simulating)' if is_simulating else 'Sensor Disconnected')
                sensor_status_lbl.classes(replace='text-green', add='text-grey')
                
            if not data and not port_online and not is_simulating:
                return
            
            temp_unit, pres_unit, flow_unit = get_effective_units(port_num)
            
            def _get_sensor_val(key, v_type):
                # Try to find value by key (either simplified ID or descriptive label)
                raw_val = data.get(key)
                if raw_val is None:
                    # Fallback: check if we have it under a descriptive name from IODD
                    smap = sensor_parser.get_sensor_map(sensor_type)
                    for k, v in smap.items():
                        if v.get('display_name') and key in v['display_name']:
                             raw_val = data.get(k)
                             break
                
                if raw_val is None: return 0.0

                # Apply scaling
                val = apply_unit_scaling(raw_val, v_type, port_num)
                
                # Keyence sensors often have a 0.1 multiplier for the base unit
                val /= 10.0
                return val

            if "MP-F" in sensor_type:
                flow = _get_sensor_val('1FlowInst', 'flow')
                # Total flow is often L or ft^3, might not need /10, but let's stay consistent with IOLink 
                # actually 1FlowTotal is usually integer L. Let's check.
                flow_tot = apply_unit_scaling(data.get('1FlowTotal', 0), 'flow_total', port_num)
                
                pressure = _get_sensor_val('1Pressure', 'pres')
                temp = _get_sensor_val('1Temperature', 'temp')
                hum = _get_sensor_val('1Humidity', 'hum')
                
                max_flow = float(settings.get(f"{port_num}_max_flow", 1000.0))
                
                elements.get('temp_knob', ui.knob()).value = round(temp, 1)
                elements.get('pres_knob', ui.knob()).value = round(pressure, 1)
                elements.get('hum_knob', ui.knob()).value = round(hum, 1)
                
                elements.get('flow_bar', ui.linear_progress()).value = min(flow / max(max_flow, 1.0), 1.0)
                elements.get('flow_lbl', ui.label()).set_text(f"{round(flow, 1)} {flow_unit}")
                elements.get('flow_tot_lbl', ui.label()).set_text(f"{round(flow_tot, 1)} {flow_unit}")
                
                # Fetch live valve state (0 = closed, 1 = open)
                v_state_raw = _get_sensor_val('1ValveState', 'boolean')
                
                if 'valve_toggle' in elements:
                    # In Keyence MP-F, ValveState 0 means closed, 1 means open
                    is_open = bool(int(v_state_raw * 10.0))  # reverse the /10.0 done in _get_sensor_val
                    elements['valve_toggle'].update_state(is_open)

            elif "GP-M" in sensor_type:
                pressure = _get_sensor_val('Pressure', 'pres')
                temp = _get_sensor_val('Temp', 'temp')
                
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
