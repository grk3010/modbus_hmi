import os
from nicegui import ui
from shared_state import settings, modbus_client, sensor_parser, IODD_DIR, get_effective_units, apply_unit_scaling, save_settings
from components import ValveToggle, GaugeSettingsDialog

@ui.page('/sensor/{port_id}')
def sensor_page(port_id: str):
    ui.add_css('''
    .text-gauge-color { color: var(--gauge-color) !important; }
    ''')
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
        # Dashboard display container for this sensor
        data_card = ui.card().classes('dashboard-card w-full max-w-4xl q-mt-md items-center overflow-hidden')
        
        elements = {}
        
        async def reset_flow(port):
            with ui.dialog() as dialog, ui.card():
                ui.label('Reset total flow?').classes('text-h6')
                ui.label('This will zero out the integrated flow for this sensor.').classes('text-body1')
                with ui.row().classes('w-full justify-end'):
                    ui.button('Cancel', on_click=dialog.close).props('flat')
                    ui.button('RESET', on_click=lambda: _do_reset(port, dialog)).props('flat color=negative')
            dialog.open()

        async def _do_reset(port, dialog):
            success = await modbus_client.reset_accumulated_flow(port)
            if success:
                ui.notify("Total flow reset successful")
            else:
                ui.notify("Reset failed - check connection", type='negative')
            dialog.close()

        @ui.refreshable
        def render_sensor_data():
            elements.clear()
            temp_unit, pres_unit, flow_unit = get_effective_units(port_num)
            
            def open_settings(metric, label):
                GaugeSettingsDialog(port_num, metric, label, on_save=update_single_card).open()

            if "MP-F" in sensor_type:
                # Main Grid (Top & Middle Rows) - Increase vertical padding
                with ui.row().classes('w-full justify-between items-start q-py-xl q-px-md no-wrap border-b border-gray-800'):
                    
                    # Left Column: Temp over Pressure - Increase gap
                    with ui.column().classes('items-center gap-24'):
                        with ui.column().classes('items-center cursor-pointer').on('click', lambda: open_settings('temp', f'Temperature ({temp_unit})')):
                            ui.label(f"Temp ({temp_unit})").classes('text-subtitle2 text-grey')
                            elements['temp_knob'] = ui.knob(0, min=-50, max=200, show_value=True).props('size="105px" track-color="dark" readonly color="gauge-color"')
                        
                        with ui.column().classes('items-center cursor-pointer').on('click', lambda: open_settings('pres', f'Pressure ({pres_unit})')):
                            ui.label(f"Pressure ({pres_unit})").classes('text-subtitle2 text-grey')
                            elements['pres_knob'] = ui.knob(0, min=0, max=200, show_value=True).props('size="105px" track-color="dark" readonly color="gauge-color"')

                    # Center Column: Image over Valve
                    with ui.column().classes('items-center justify-between self-stretch py-2'):
                        if img_src:
                            rel_src = f"/iodd_assets/{os.path.relpath(img_src, os.path.abspath(IODD_DIR))}"
                            ui.image(rel_src).classes('w-48 h-48 object-cover aspect-square bg-white rounded-lg shadow-md border border-gray-700').props('fit="contain"')
                        
                        with ui.column().classes('items-center mt-12'): # Added specific margin top
                            ui.label("VALVE").classes('text-subtitle2 text-grey-5 font-bold')
                            elements['valve_toggle'] = ValveToggle(port_num, initial_state=False, client=modbus_client).classes('scale-90')

                    # Right Column: Humidity over Flow Rate - Increase gap
                    with ui.column().classes('items-center gap-24'):
                        with ui.column().classes('items-center cursor-pointer').on('click', lambda: open_settings('hum', 'Humidity (%)')):
                            ui.label(f"Humidity (%)").classes('text-subtitle2 text-grey')
                            elements['hum_knob'] = ui.knob(0, min=0, max=100, show_value=True).props('size="105px" track-color="dark" readonly color="gauge-color"')

                        with ui.column().classes('items-center cursor-pointer').on('click', lambda: open_settings('flow', f'Flow Rate ({flow_unit})')):
                            ui.label(f"Flow Rate ({flow_unit})").classes('text-subtitle2 text-grey')
                            elements['flow_knob'] = ui.knob(0, min=0, max=200, show_value=True).props('size="105px" track-color="dark" readonly color="gauge-color"')

                # Bottom Row: Total Flow & Reset Button
                with ui.row().classes('w-full justify-center items-center q-pa-sm bg-black/20 rounded-b gap-8'):
                    with ui.row().classes('items-center gap-3'):
                        ui.label("TOTAL FL:").classes('text-subtitle1 text-grey-5 font-bold')
                        elements['flow_tot_lbl'] = ui.label(f"0 {flow_unit}").classes('text-h6 text-white text-bold')
                    
                    ui.button("RESET", on_click=lambda: reset_flow(port_num)).classes('w-[168px] h-[72px] rounded-full border-4 border-solid border-white text-white font-bold text-lg tracking-wider shadow-sm shrink-0 scale-90').style('background-color: #303030 !important').props('unelevated no-caps')

            elif "GP-M" in sensor_type:
                # GP-M Layout: Image center, Knobs left/right
                with ui.row().classes('w-full justify-around items-center q-pa-lg'):
                    with ui.column().classes('items-center cursor-pointer').on('click', lambda: open_settings('pres', f'Pressure ({pres_unit})')):
                        ui.label(f"Pressure ({pres_unit})").classes('text-h6 text-grey')
                        elements['pres_knob'] = ui.knob(0, min=-50, max=200, show_value=True).props('size="160px" track-color="dark" readonly color="gauge-color"')
                    
                    if img_src:
                        rel_src = f"/iodd_assets/{os.path.relpath(img_src, os.path.abspath(IODD_DIR))}"
                        ui.image(rel_src).classes('w-48 h-48 object-cover aspect-square bg-white rounded-lg shadow-md border border-gray-700').props('fit="contain"')

                    with ui.column().classes('items-center cursor-pointer').on('click', lambda: open_settings('temp', f'Temperature ({temp_unit})')):
                        ui.label(f"Temp ({temp_unit})").classes('text-h6 text-grey')
                        elements['temp_knob'] = ui.knob(0, min=-50, max=200, show_value=True).props('size="160px" track-color="dark" readonly color="gauge-color"')
            else:
                elements['generic'] = ui.label("Generic Sensor Data").classes('text-h6 text-grey q-pa-xl')
                
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
                flow_tot = apply_unit_scaling(data.get('1FlowTotal', 0), 'flow_total', port_num)
                pressure = _get_sensor_val('1Pressure', 'pres')
                temp = _get_sensor_val('1Temperature', 'temp')
                hum = _get_sensor_val('1Humidity', 'hum')
                
                def update_knob(el_key, val, metric_name, default_max, default_caut, default_warn, default_color_norm, default_color_caut, default_color_warn):
                    knob = elements.get(el_key)
                    if not knob: return
                    
                    max_val = float(settings.get(f"{port_num}_{metric_name}_max", default_max))
                    caut_val = float(settings.get(f"{port_num}_{metric_name}_caution", default_caut))
                    warn_val = float(settings.get(f"{port_num}_{metric_name}_warn", default_warn))
                    
                    color_norm = settings.get(f"{port_num}_{metric_name}_color_norm", default_color_norm)
                    color_caut = settings.get(f"{port_num}_{metric_name}_color_caut", default_color_caut)
                    color_warn = settings.get(f"{port_num}_{metric_name}_color_warn", default_color_warn)
                    
                    knob.value = round(val, 1)
                    
                    if val >= warn_val:
                        color = color_warn
                    elif val >= caut_val:
                        color = color_caut
                    else:
                        color = color_norm
                        
                    # Target both the text and arc (via inherited style)
                    knob.value = round(val, 1)
                    knob.props(f'max={max_val}')
                    knob.style(f'--gauge-color: {color} !important; color: {color} !important')
                    knob.update()

                # Enforce Defaults: Temp 200, Pres 200, Hum 100, Flow 200
                update_knob('temp_knob', temp, 'temp', 200, 160, 180, "#ef4444", "#f59e0b", "#991b1b")
                update_knob('pres_knob', pressure, 'pres', 200, 160, 180, "#f59e0b", "#fbbf24", "#ef4444")
                update_knob('hum_knob', hum, 'hum', 100, 80, 90, "#3b82f6", "#60a5fa", "#2563eb")
                update_knob('flow_knob', flow, 'flow', 200, 160, 180, "#3b82f6", "#60a5fa", "#2563eb")

                if tot_lbl := elements.get('flow_tot_lbl'):
                    tot_lbl.set_text(f"{round(flow_tot, 1)} {flow_unit}")
                
                v_raw = _get_sensor_val('1ValveState', 'boolean')
                if toggle := elements.get('valve_toggle'):
                    toggle.update_state(bool(int(v_raw * 10.0)))

            elif "GP-M" in sensor_type:
                pressure = _get_sensor_val('Pressure', 'pres')
                temp = _get_sensor_val('Temp', 'temp')
                
                def update_knob(el_key, val, metric_name, default_max, default_caut, default_warn, default_color_norm, default_color_caut, default_color_warn):
                    knob = elements.get(el_key)
                    if not knob: return
                    max_val = float(settings.get(f"{port_num}_{metric_name}_max", default_max))
                    caut_val = float(settings.get(f"{port_num}_{metric_name}_caution", default_caut))
                    warn_val = float(settings.get(f"{port_num}_{metric_name}_warn", default_warn))
                    
                    color_norm = settings.get(f"{port_num}_{metric_name}_color_norm", default_color_norm)
                    color_caut = settings.get(f"{port_num}_{metric_name}_color_caut", default_color_caut)
                    color_warn = settings.get(f"{port_num}_{metric_name}_color_warn", default_color_warn)
                    
                    knob.value = round(val, 1)
                    if val >= warn_val:
                        color = color_warn
                    elif val >= caut_val:
                        color = color_caut
                    else:
                        color = color_norm
                    
                    knob.value = round(val, 1)
                    knob.props(f'max={max_val}')
                    knob.style(f'--gauge-color: {color} !important; color: {color} !important')
                    knob.update()

                update_knob('pres_knob', pressure, 'pres', 200, 160, 180, "#f59e0b", "#fbbf24", "#ef4444")
                update_knob('temp_knob', temp, 'temp', 200, 160, 180, "#ef4444", "#f59e0b", "#991b1b")
            else:
                gen_lbl = elements.get('generic')
                if gen_lbl:
                    gen_lbl.set_text(", ".join([f"{k}: {v}" for k, v in data.items()]))

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
