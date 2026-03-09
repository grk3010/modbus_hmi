import os
from nicegui import ui
from shared_state import settings, modbus_client, opcua_client, get_effective_units, apply_unit_scaling

@ui.page('/')
def index():
    with ui.header().classes('bg-dark text-white items-center q-pa-md shadow-2'):
        ui.label('Compressor Room Dashboard').classes('text-h5 font-bold tracking-wide')
        ui.space()
        with ui.row().classes('items-center gap-4'):
            with ui.row().classes('items-center gap-2'):
                global_status = ui.image('/iodd_assets/assets/disconnected.png').classes('w-6 h-6 object-contain')
                ui.label('I-O Link Master').classes('text-subtitle1 text-grey')
        ui.space()
        ui.button('Charts', icon='show_chart', on_click=lambda: ui.navigate.to('/charts')).props('flat')
        ui.button('Configuration', icon='settings', on_click=lambda: ui.navigate.to('/config')).props('flat')

    gp_pic = "/iodd_assets/extracted_KEYENCE_GP-MT_IO-Link_V1_0/KEYENCE_GP-MT_IO-Link_V1_0/KEYENCE-GP-MT-pic.png"
    mp_pic = "/iodd_assets/extracted_mp_f/KEYENCE_MP-F_IO-Link_V1_0/KEYENCE-MP-F80-pic.png"

    gp_ports = [p for p, t in settings.items() if p.isdigit() and "GP-M" in t]
    mp_ports = [p for p, t in settings.items() if p.isdigit() and "MP-F" in t]
    
    # Fallback to sensible defaults if unconfigured
    # Map detected sensors to slots while ensuring absolute uniqueness across all slots
    used_ports = set()
    
    # First, reserve all manually assigned ports
    manual_slots = ["slot_gp1", "slot_gp2", "slot_mp1", "slot_mp2", "slot_mp3"]
    for s_key in manual_slots:
        val = settings.get(s_key, "Auto")
        if val != "Auto":
            used_ports.add(str(val))

    def assign_unique(slot_key, ports_list, index, default_p):
        # 1. Check for manual override
        manual_val = settings.get(slot_key, "Auto")
        if manual_val != "Auto":
            return str(manual_val)
            
        # 2. Try auto-detection if not overridden
        port = ports_list[index] if len(ports_list) > index else default_p
        
        # If this port is already assigned (manually or previously auto-assigned), 
        # pick the next available numeric ID
        p_val = int(port) if port.isdigit() else 1
        while str(port) in used_ports:
            p_val += 1
            port = str(p_val)
            
        used_ports.add(str(port))
        return str(port)

    # Assign roles based on common layout: GP for tanks, MP for outlets
    gp1 = assign_unique("slot_gp1", gp_ports, 0, "2")
    gp2 = assign_unique("slot_gp2", gp_ports, 1, "3")
    mp1 = assign_unique("slot_mp1", mp_ports, 0, "1")
    mp2 = assign_unique("slot_mp2", mp_ports, 1, "4")
    mp3 = assign_unique("slot_mp3", mp_ports, 2, "5")

    ui_elements = {}

    # Custom CSS to manage visibility breakpoints because Tailwind's hidden md:block 
    # clashes with nested absolute positioning in NiceGUI under certain conditions.
    ui.add_head_html('''
        <style>
            .desktop-view { display: none !important; }
            .mobile-view { display: flex !important; }
            @media (min-width: 768px) {
                .desktop-view { display: block !important; }
                .mobile-view { display: none !important; }
            }
            .red-x-container {
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                pointer-events: none;
                z-index: 30;
                display: flex;
                align-items: center;
                justify-content: center;
            }
        </style>
    ''')

    with ui.element('div').classes('w-full flex justify-center items-center q-pa-md'):
        
        # --- DESKTOP VIEW (Hidden on Mobile) ---
        # Container
        with ui.element('div').classes('desktop-view relative w-full max-w-[1400px] shadow-2xl rounded-xl overflow-hidden bg-black/50 border border-gray-800'):
            # Background
            ui.image('/iodd_assets/assets/compressor_dashboard.png').classes('w-full h-auto block opacity-90')
            
            # Interactive Zones
            # 1. Compressor
            ui.element('div').classes('absolute compressor-zone z-10').style('top: 15%; left: 3%; width: 28%; height: 70%;').on('click', lambda: ui.navigate.to('/compressor'))
            
            # Compressor Status Tooltip
            with ui.element('div').classes('absolute flex items-center gap-2 live-badge z-20').style('top: 25%; left: 8%;'):
                ui.icon('power', color='green').classes('text-xl')
                ui_elements['comp_status'] = ui.label('Ready')

            # 2. GP-M010T #1 (Wet Tank Out)
            with ui.element('div').classes('absolute flex flex-col items-center interactive-element z-20 cursor-pointer').style('top: 18%; left: 47%;').on('click', lambda: ui.navigate.to(f'/sensor/{gp1}')):
                ui.label(settings.get(f"{gp1}_name") or 'Wet Air').classes('text-white font-bold select-none drop-shadow-md q-mb-xs')
                with ui.element('div').classes('relative'):
                    ui.image(gp_pic).classes('w-20 h-auto filter opacity-50 rounded-xl bg-white/10 p-2 drop-shadow hover:brightness-125 hover:opacity-100 transition-all')
                    with ui.element('div').classes('red-x-container') as x:
                        ui_elements['gp1_x'] = x
                        ui.html('<svg width="100%" height="100%" viewBox="0 0 100 100" preserveAspectRatio="none"><line x1="10" y1="10" x2="90" y2="90" stroke="red" stroke-width="4"/><line x1="90" y1="10" x2="10" y2="90" stroke="red" stroke-width="4"/></svg>')
                with ui.row().classes('live-badge q-mt-sm whitespace-nowrap'):
                    ui_elements['gp1_val'] = ui.label('---')
            
            # 3. GP-M010T #2 (Dry Tank In)
            with ui.element('div').classes('absolute flex flex-col items-center interactive-element z-20 cursor-pointer').style('top: 61%; left: 65%;').on('click', lambda: ui.navigate.to(f'/sensor/{gp2}')):
                ui.label(settings.get(f"{gp2}_name") or 'Dry Air').classes('text-white font-bold select-none drop-shadow-md q-mb-xs')
                with ui.element('div').classes('relative'):
                    ui.image(gp_pic).classes('w-20 h-auto filter opacity-50 rounded-xl bg-white/10 p-2 drop-shadow hover:brightness-125 hover:opacity-100 transition-all')
                    with ui.element('div').classes('red-x-container') as x:
                        ui_elements['gp2_x'] = x
                        ui.html('<svg width="100%" height="100%" viewBox="0 0 100 100" preserveAspectRatio="none"><line x1="10" y1="10" x2="90" y2="90" stroke="red" stroke-width="4"/><line x1="90" y1="10" x2="10" y2="90" stroke="red" stroke-width="4"/></svg>')
                with ui.row().classes('live-badge q-mt-sm whitespace-nowrap'):
                    ui_elements['gp2_val'] = ui.label('---')

            # 4. MP-FN80 #1 (Outlet 1)
            with ui.element('div').classes('absolute flex flex-col items-center interactive-element z-20 cursor-pointer').style('top: 18%; left: 92%;').on('click', lambda: ui.navigate.to(f'/sensor/{mp1}')):
                ui.label(settings.get(f"{mp1}_name") or 'Outlet 1').classes('text-white font-bold select-none drop-shadow-md q-mb-xs')
                with ui.element('div').classes('relative'):
                    ui.image(mp_pic).classes('w-16 h-auto filter opacity-50 rounded-xl bg-white/10 p-2 drop-shadow hover:brightness-125 hover:opacity-100 transition-all')
                    with ui.element('div').classes('red-x-container') as x:
                        ui_elements['mp1_x'] = x
                        ui.html('<svg width="100%" height="100%" viewBox="0 0 100 100" preserveAspectRatio="none"><line x1="10" y1="10" x2="90" y2="90" stroke="red" stroke-width="4"/><line x1="90" y1="10" x2="10" y2="90" stroke="red" stroke-width="4"/></svg>')
                with ui.column().classes('live-badge q-mt-sm items-center gap-0'):
                    ui_elements['mp1_flow'] = ui.label('---')
                    ui_elements['mp1_pres'] = ui.label('---')

            # 5. MP-FN80 #2 (Outlet 2)
            with ui.element('div').classes('absolute flex flex-col items-center interactive-element z-20 cursor-pointer').style('top: 43%; left: 92%;').on('click', lambda: ui.navigate.to(f'/sensor/{mp2}')):
                ui.label(settings.get(f"{mp2}_name") or 'Outlet 2').classes('text-white font-bold select-none drop-shadow-md q-mb-xs')
                with ui.element('div').classes('relative'):
                    ui.image(mp_pic).classes('w-16 h-auto filter opacity-50 rounded-xl bg-white/10 p-2 drop-shadow hover:brightness-125 hover:opacity-100 transition-all')
                    with ui.element('div').classes('red-x-container') as x:
                        ui_elements['mp2_x'] = x
                        ui.html('<svg width="100%" height="100%" viewBox="0 0 100 100" preserveAspectRatio="none"><line x1="10" y1="10" x2="90" y2="90" stroke="red" stroke-width="4"/><line x1="90" y1="10" x2="10" y2="90" stroke="red" stroke-width="4"/></svg>')
                with ui.column().classes('live-badge q-mt-sm items-center gap-0'):
                    ui_elements['mp2_flow'] = ui.label('---')
                    ui_elements['mp2_pres'] = ui.label('---')

            # 6. MP-FN80 #3 (Outlet 3)
            with ui.element('div').classes('absolute flex flex-col items-center interactive-element z-20 cursor-pointer').style('top: 65%; left: 92%;').on('click', lambda: ui.navigate.to(f'/sensor/{mp3}')):
                ui.label(settings.get(f"{mp3}_name") or 'Outlet 3').classes('text-white font-bold select-none drop-shadow-md q-mb-xs')
                with ui.element('div').classes('relative'):
                    ui.image(mp_pic).classes('w-16 h-auto filter opacity-50 rounded-xl bg-white/10 p-2 drop-shadow hover:brightness-125 hover:opacity-100 transition-all')
                    with ui.element('div').classes('red-x-container') as x:
                        ui_elements['mp3_x'] = x
                        ui.html('<svg width="100%" height="100%" viewBox="0 0 100 100" preserveAspectRatio="none"><line x1="10" y1="10" x2="90" y2="90" stroke="red" stroke-width="4"/><line x1="90" y1="10" x2="10" y2="90" stroke="red" stroke-width="4"/></svg>')
                with ui.column().classes('live-badge q-mt-sm items-center gap-0'):
                    ui_elements['mp3_flow'] = ui.label('---')
                    ui_elements['mp3_pres'] = ui.label('---')
        
        # --- MOBILE VIEW (Hidden on Desktop) ---
        with ui.column().classes('mobile-view w-full gap-4'):
            
            # Compressor Card
            with ui.card().classes('w-full bg-dark bg-opacity-80 p-4 border border-gray-700 cursor-pointer').on('click', lambda: ui.navigate.to('/compressor')):
                with ui.row().classes('items-center gap-4'):
                    ui.icon('power', color='green').classes('text-4xl')
                    with ui.column().classes('gap-0'):
                        ui.label('Atlas Copco VSDS').classes('text-lg font-bold')
                        ui_elements['comp_status_mob'] = ui.label('Ready').classes('text-grey')

            # GP-M Cards
            for p, name_fallback, key_prefix in [(gp1, 'Wet Air', 'gp1'), (gp2, 'Dry Air', 'gp2')]:
                # We need a proper closure for the loop variables to avoid lambda bleeding
                def _make_gp_card(port, fb_name, ui_key):
                    name = settings.get(f"{port}_name") or fb_name
                    with ui.card().classes('w-full bg-dark bg-opacity-80 p-4 border border-gray-700 cursor-pointer').on('click', lambda: ui.navigate.to(f'/sensor/{port}')):
                        with ui.row().classes('items-center justify-between w-full'):
                            with ui.row().classes('items-center gap-4'):
                                with ui.element('div').classes('relative w-12 h-12'):
                                    ui.image(gp_pic).classes('w-full h-full object-contain filter opacity-80')
                                    with ui.element('div').classes('red-x-container') as x:
                                        ui_elements[f'{ui_key}_x_mob'] = x
                                        ui.html('<svg width="100%" height="100%" viewBox="0 0 100 100" preserveAspectRatio="none"><line x1="10" y1="10" x2="90" y2="90" stroke="red" stroke-width="4"/><line x1="90" y1="10" x2="10" y2="90" stroke="red" stroke-width="4"/></svg>')
                                ui.label(name).classes('text-lg font-bold')
                            ui_elements[f'{ui_key}_val_mob'] = ui.label('---').classes('text-xl text-primary font-bold')
                _make_gp_card(p, name_fallback, key_prefix)
                
            # MP-F Cards
            for p, name_fallback, key_prefix in [(mp1, 'Outlet 1', 'mp1'), (mp2, 'Outlet 2', 'mp2'), (mp3, 'Outlet 3', 'mp3')]:
                def _make_mp_card(port, fb_name, ui_key):
                    name = settings.get(f"{port}_name") or fb_name
                    with ui.card().classes('w-full bg-dark bg-opacity-80 p-4 border border-gray-700 cursor-pointer').on('click', lambda: ui.navigate.to(f'/sensor/{port}')):
                        with ui.row().classes('items-center justify-between w-full'):
                            with ui.row().classes('items-center gap-4'):
                                with ui.element('div').classes('relative w-12 h-12'):
                                    ui.image(mp_pic).classes('w-12 h-12 object-contain filter opacity-80')
                                    with ui.element('div').classes('red-x-container') as x:
                                        ui_elements[f'{ui_key}_x_mob'] = x
                                        ui.html('<svg width="100%" height="100%" viewBox="0 0 100 100" preserveAspectRatio="none"><line x1="10" y1="10" x2="90" y2="90" stroke="red" stroke-width="4"/><line x1="90" y1="10" x2="10" y2="90" stroke="red" stroke-width="4"/></svg>')
                                ui.label(name).classes('text-lg font-bold')
                            with ui.column().classes('gap-0 items-end'):
                                ui_elements[f'{ui_key}_flow_mob'] = ui.label('---').classes('text-lg text-primary font-bold')
                                ui_elements[f'{ui_key}_pres_mob'] = ui.label('---').classes('text-sm text-secondary')
                _make_mp_card(p, name_fallback, key_prefix)
                    
    def update_cards():
        if modbus_client.master_online:
            global_status.set_source('/iodd_assets/assets/connected.png')
        else:
            global_status.set_source('/iodd_assets/assets/disconnected.png')
            
        # Update Compressor status
        if opcua_client and opcua_client.connected:
            comp_state = "RUNNING" if opcua_client.data.get("running") else "STOPPED"
            comp_lbl = f"{comp_state} | {opcua_client.data.get('pressure', 0):.1f} kPa"
            ui_elements['comp_status'].set_text(comp_lbl)
            ui_elements['comp_status_mob'].set_text(comp_lbl)
        else:
            ui_elements['comp_status'].set_text("OFFLINE")
            ui_elements['comp_status_mob'].set_text("OFFLINE")
            
        def _get_val(p, key, unit, v_type):
            is_simulating = settings.get("use_simulation", False)
            data = {}
            if is_simulating:
                import random
                s_type = settings.get(str(p), "")
                if "MP-F" in s_type:
                    data = {
                        '1FlowInst': random.uniform(10, 500) * 10,
                        '1Pressure': random.uniform(50, 800)
                    }
                elif "GP-M" in s_type:
                    data = {
                        'Pressure': random.uniform(0, 5000),
                        'Temp': random.uniform(200, 800)
                    }
            else:
                data = modbus_client.port_data.get(int(p), {})
            
            if not data: return '---'

            # Try to find value by key (either simplified ID or descriptive label)
            raw_val = data.get(key)
            if raw_val is None:
                # Fallback: check if we have it under a descriptive name from IODD
                pid = settings.get(str(p))
                smap = sensor_parser.get_sensor_map(pid)
                for k, v in smap.items():
                    if v.get('display_name') and key in v['display_name']:
                         raw_val = data.get(k)
                         break
            
            if raw_val is None: return '---'

            # Apply scaling
            val = apply_unit_scaling(raw_val, v_type, int(p))
            
            # Keyence sensors often have a 0.1 multiplier for the base unit 
            # (e.g. 100 on Modbus = 10.0 kPa or 10.0 L/min)
            # This applies to MP-FN Flow/Pres and GP-M Temp/Pres
            val /= 10.0
            
            return f"{val:.1f} {unit}"

        # Get units
        t_gp1, p_gp1, _ = get_effective_units(int(gp1))
        t_gp2, p_gp2, _ = get_effective_units(int(gp2))
        _, p_mp1, f_mp1 = get_effective_units(int(mp1))
        _, p_mp2, f_mp2 = get_effective_units(int(mp2))
        _, p_mp3, f_mp3 = get_effective_units(int(mp3))

        # Update sensors visually if online
        v_gp1 = _get_val(gp1, 'Pressure', p_gp1, 'pres')
        ui_elements['gp1_val'].set_text(v_gp1)
        ui_elements['gp1_val_mob'].set_text(v_gp1)
        
        v_gp2 = _get_val(gp2, 'Pressure', p_gp2, 'pres')
        ui_elements['gp2_val'].set_text(v_gp2)
        ui_elements['gp2_val_mob'].set_text(v_gp2)
        
        f_m1 = _get_val(mp1, '1FlowInst', f_mp1, 'flow')
        p_m1 = _get_val(mp1, '1Pressure', p_mp1, 'pres')
        ui_elements['mp1_flow'].set_text(f_m1)
        ui_elements['mp1_pres'].set_text(p_m1)
        ui_elements['mp1_flow_mob'].set_text(f_m1)
        ui_elements['mp1_pres_mob'].set_text(p_m1)
        
        f_m2 = _get_val(mp2, '1FlowInst', f_mp2, 'flow')
        p_m2 = _get_val(mp2, '1Pressure', p_mp2, 'pres')
        ui_elements['mp2_flow'].set_text(f_m2)
        ui_elements['mp2_pres'].set_text(p_m2)
        ui_elements['mp2_flow_mob'].set_text(f_m2)
        ui_elements['mp2_pres_mob'].set_text(p_m2)
        
        f_m3 = _get_val(mp3, '1FlowInst', f_mp3, 'flow')
        p_m3 = _get_val(mp3, '1Pressure', p_mp3, 'pres')
        ui_elements['mp3_flow'].set_text(f_m3)
        ui_elements['mp3_pres'].set_text(p_m3)
        ui_elements['mp3_flow_mob'].set_text(f_m3)
        ui_elements['mp3_pres_mob'].set_text(p_m3)

        # Update Red X overlays based on actual port status
        is_sim = settings.get("use_simulation", False)
        for p, key in [(gp1, 'gp1'), (gp2, 'gp2'), (mp1, 'mp1'), (mp2, 'mp2'), (mp3, 'mp3')]:
            status = modbus_client.port_status.get(int(p), False) if not is_sim else True
            if f'{key}_x' in ui_elements:
                ui_elements[f'{key}_x'].set_visibility(not status)
            if f'{key}_x_mob' in ui_elements:
                ui_elements[f'{key}_x_mob'].set_visibility(not status)

    ui.timer(1.0, update_cards)
