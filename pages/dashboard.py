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
    gp1 = gp_ports[0] if len(gp_ports) > 0 else "1"
    gp2 = gp_ports[1] if len(gp_ports) > 1 else "2"
    mp1 = mp_ports[0] if len(mp_ports) > 0 else "3"
    mp2 = mp_ports[1] if len(mp_ports) > 1 else "4"
    mp3 = mp_ports[2] if len(mp_ports) > 2 else "5"

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
                ui.image(gp_pic).classes('w-20 h-auto filter opacity-50 rounded-xl bg-white/10 p-2 drop-shadow hover:brightness-125 hover:opacity-100 transition-all')
                with ui.row().classes('live-badge q-mt-sm whitespace-nowrap'):
                    ui_elements['gp1_val'] = ui.label('---')
            
            # 3. GP-M010T #2 (Dry Tank In)
            with ui.element('div').classes('absolute flex flex-col items-center interactive-element z-20 cursor-pointer').style('top: 61%; left: 65%;').on('click', lambda: ui.navigate.to(f'/sensor/{gp2}')):
                ui.label(settings.get(f"{gp2}_name") or 'Dry Air').classes('text-white font-bold select-none drop-shadow-md q-mb-xs')
                ui.image(gp_pic).classes('w-20 h-auto filter opacity-50 rounded-xl bg-white/10 p-2 drop-shadow hover:brightness-125 hover:opacity-100 transition-all')
                with ui.row().classes('live-badge q-mt-sm whitespace-nowrap'):
                    ui_elements['gp2_val'] = ui.label('---')

            # 4. MP-FN80 #1 (Outlet 1)
            with ui.element('div').classes('absolute flex flex-col items-center interactive-element z-20 cursor-pointer').style('top: 18%; left: 92%;').on('click', lambda: ui.navigate.to(f'/sensor/{mp1}')):
                ui.label(settings.get(f"{mp1}_name") or 'Outlet 1').classes('text-white font-bold select-none drop-shadow-md q-mb-xs')
                ui.image(mp_pic).classes('w-16 h-auto filter opacity-50 rounded-xl bg-white/10 p-2 drop-shadow hover:brightness-125 hover:opacity-100 transition-all')
                with ui.column().classes('live-badge q-mt-sm items-center gap-0'):
                    ui_elements['mp1_flow'] = ui.label('---')
                    ui_elements['mp1_pres'] = ui.label('---')

            # 5. MP-FN80 #2 (Outlet 2)
            with ui.element('div').classes('absolute flex flex-col items-center interactive-element z-20 cursor-pointer').style('top: 43%; left: 92%;').on('click', lambda: ui.navigate.to(f'/sensor/{mp2}')):
                ui.label(settings.get(f"{mp2}_name") or 'Outlet 2').classes('text-white font-bold select-none drop-shadow-md q-mb-xs')
                ui.image(mp_pic).classes('w-16 h-auto filter opacity-50 rounded-xl bg-white/10 p-2 drop-shadow hover:brightness-125 hover:opacity-100 transition-all')
                with ui.column().classes('live-badge q-mt-sm items-center gap-0'):
                    ui_elements['mp2_flow'] = ui.label('---')
                    ui_elements['mp2_pres'] = ui.label('---')

            # 6. MP-FN80 #3 (Outlet 3)
            with ui.element('div').classes('absolute flex flex-col items-center interactive-element z-20 cursor-pointer').style('top: 65%; left: 92%;').on('click', lambda: ui.navigate.to(f'/sensor/{mp3}')):
                ui.label(settings.get(f"{mp3}_name") or 'Outlet 3').classes('text-white font-bold select-none drop-shadow-md q-mb-xs')
                ui.image(mp_pic).classes('w-16 h-auto filter opacity-50 rounded-xl bg-white/10 p-2 drop-shadow hover:brightness-125 hover:opacity-100 transition-all')
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
            for p, name_fallback, key in [(gp1, 'Wet Air', 'gp1_val'), (gp2, 'Dry Air', 'gp2_val')]:
                # We need a proper closure for the loop variables to avoid lambda bleeding
                def _make_gp_card(port, fb_name, ui_key):
                    name = settings.get(f"{port}_name") or fb_name
                    with ui.card().classes('w-full bg-dark bg-opacity-80 p-4 border border-gray-700 cursor-pointer').on('click', lambda: ui.navigate.to(f'/sensor/{port}')):
                        with ui.row().classes('items-center justify-between w-full'):
                            with ui.row().classes('items-center gap-4'):
                                ui.image(gp_pic).classes('w-12 h-12 object-contain filter opacity-80')
                                ui.label(name).classes('text-lg font-bold')
                            ui_elements[f'{ui_key}_mob'] = ui.label('---').classes('text-xl text-primary font-bold')
                _make_gp_card(p, name_fallback, key)
                
            # MP-F Cards
            for p, name_fallback, key_prefix in [(mp1, 'Outlet 1', 'mp1'), (mp2, 'Outlet 2', 'mp2'), (mp3, 'Outlet 3', 'mp3')]:
                def _make_mp_card(port, fb_name, ui_key):
                    name = settings.get(f"{port}_name") or fb_name
                    with ui.card().classes('w-full bg-dark bg-opacity-80 p-4 border border-gray-700 cursor-pointer').on('click', lambda: ui.navigate.to(f'/sensor/{port}')):
                        with ui.row().classes('items-center justify-between w-full'):
                            with ui.row().classes('items-center gap-4'):
                                ui.image(mp_pic).classes('w-12 h-12 object-contain filter opacity-80')
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
            if is_simulating:
                import random
                s_type = settings.get(str(p), "")
                val = 0.0
                if "MP-F" in s_type:
                    if key == '1FlowInst': val = random.uniform(10, 500) * 10
                    elif key == '1Pressure': val = random.uniform(50, 800)
                elif "GP-M" in s_type:
                    if key == 'Pressure': val = random.uniform(0, 5000)
                    elif key == 'Temp': val = random.uniform(200, 800)
                
                val = apply_unit_scaling(val, v_type, int(p))
                if v_type in ('temp', 'hum'): val /= 10.0
                return f"{val:.1f} {unit}"

            data = modbus_client.port_data.get(int(p), {})
            if not data: return '---'
            val = apply_unit_scaling(data.get(key, 0), v_type, int(p))
            if v_type in ('temp', 'hum'): val /= 10.0
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

    ui.timer(1.0, update_cards)
