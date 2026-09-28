from nicegui import ui
import os
from shared_state import settings, data_logger, sensor_parser, IODD_DIR, get_effective_units, apply_unit_scaling

@ui.page('/charts')
def charts_page():
    with ui.header().classes('bg-dark text-white items-center q-pa-md shadow-2'):
        ui.button(icon='arrow_back', on_click=lambda: ui.navigate.to('/')).props('flat')
        ui.label('Historical Data').classes('text-h5 font-bold')
        ui.space()
        with ui.row().classes('items-center gap-3'):
            ui.label("Time Window:").classes('text-bold text-grey-4 text-sm')
            hours_select = ui.select({1: 'Last 1 Hour', 6: 'Last 6 Hours', 24: 'Last 24 Hours', 168: 'Last 1 Week', 720: 'Last 1 Month', 0: 'Custom Range'}, value=1).classes('w-40').props('dark rounded outlined dense')
            
            ui.label("Start:").classes('text-bold text-grey-4 text-sm q-ml-sm')
            with ui.input().props('dark rounded outlined dense').classes('w-32') as start_date_input:
                with ui.menu().props('no-parent-event max-height=500px').classes('bg-[#1a1c1e] p-2').style('min-width: 310px; min-height: 400px;') as start_menu:
                    with ui.date().bind_value(start_date_input).props('dark').on('update:model-value', start_menu.close):
                        pass
                with start_date_input.add_slot('append'):
                    ui.icon('event').on('click', start_menu.open).classes('cursor-pointer text-grey-4')
                    
            ui.label("End:").classes('text-bold text-grey-4 text-sm q-ml-xs')
            with ui.input().props('dark rounded outlined dense').classes('w-32') as end_date_input:
                with ui.menu().props('no-parent-event max-height=500px').classes('bg-[#1a1c1e] p-2').style('min-width: 310px; min-height: 400px;') as end_menu:
                    with ui.date().bind_value(end_date_input).props('dark').on('update:model-value', end_menu.close):
                        pass
                with end_date_input.add_slot('append'):
                    ui.icon('event').on('click', end_menu.open).classes('cursor-pointer text-grey-4')

            refresh_btn = ui.button(icon='refresh', on_click=lambda: fetch_and_render()).props('flat round size=sm color=primary').tooltip('Refresh Chart')
        ui.space()
        # Logging status notification (right side of title bar)
        if not settings.get("enable_logging", False):
            with ui.row().classes('items-center gap-2 bg-red-900/40 text-red-200 px-3 py-1 rounded border border-red-700'):
                ui.icon('warning', size='sm')
                ui.label("Logging disabled").classes('text-xs')
                ui.button("Enable", on_click=lambda: ui.navigate.to('/config')).props('flat size=xs').classes('text-white underline')
        
    with ui.column().classes('w-full q-pa-sm items-center gap-2'):
        # Global cache to store current events so chart click listener can retrieve them
        current_events_cache = []
        
        def on_chart_click(e):
            try:
                args = e.args
                if isinstance(args, dict) and args.get('seriesName') == 'Events':
                    data_idx = args.get('dataIndex')
                    if current_events_cache and 0 <= data_idx < len(current_events_cache):
                        ev = current_events_cache[data_idx]
                        with ui.dialog() as dlg, ui.card().classes('bg-[#1a1c1e] text-white border-2 border-gray-700 p-6 w-96 shadow-2xl'):
                            with ui.row().classes('w-full items-center justify-between pb-2 border-b border-gray-800'):
                                with ui.row().classes('items-center gap-2'):
                                    icon_name = 'warning' if ev['type'] == 'power' else ('water_drop' if 'on' in ev['type'] else 'invert_colors_off')
                                    ui.icon(icon_name, size='sm').style(f'color: {ev["color"]}')
                                    ui.label(ev['title']).classes('text-lg font-bold').style(f'color: {ev["color"]}')
                                ui.button(icon='close', on_click=dlg.close).props('flat round size=sm text-grey')
                            
                            import datetime
                            dt_str = datetime.datetime.fromtimestamp(ev['timestamp']/1000.0).strftime('%Y-%m-%d %H:%M:%S')
                            ui.label(f"Time: {dt_str}").classes('text-xs text-grey-4 mt-2 font-mono')
                            ui.label(ev['description']).classes('text-sm text-grey-2 mt-3')
                            
                            with ui.row().classes('w-full justify-end mt-4'):
                                ui.button('Close', on_click=dlg.close).props('dense flat color=primary')
                        dlg.open()
            except Exception as ex:
                print(f"Chart click error: {ex}")

        chart_card = ui.card().classes('w-full max-w-[1200px] bg-dark text-white p-4 shadow-2')
        with chart_card:
            # We will populate the options dynamically
            chart = ui.echart({
                'tooltip': {'trigger': 'axis'},
                'legend': {'data': [], 'textStyle': {'color': '#ccc'}, 'bottom': 0},
                'grid': {'left': '5%', 'right': '5%', 'top': '10%', 'bottom': '18%', 'containLabel': True},
                'xAxis': {'type': 'time', 'splitLine': {'show': False}, 'axisLabel': {'color': '#ccc'}},
                'yAxis': [
                    {'type': 'value', 'name': 'Pres', 'position': 'left', 'offset': 0, 'axisLabel': {'color': '#ffd700'}, 'nameTextStyle': {'color': '#ffd700', 'padding': [0, 0, 0, 10]}, 'splitLine': {'lineStyle': {'color': '#333'}}},
                    {'type': 'value', 'name': 'Flow', 'position': 'left', 'offset': 60, 'axisLabel': {'color': '#00ffff'}, 'nameTextStyle': {'color': '#00ffff', 'padding': [0, 0, 0, 10]}, 'splitLine': {'show': False}},
                    {'type': 'value', 'name': 'Temp', 'position': 'right', 'offset': 0, 'axisLabel': {'color': '#ff4500'}, 'nameTextStyle': {'color': '#ff4500', 'padding': [0, 10, 0, 0]}, 'splitLine': {'show': False}},
                    {'type': 'value', 'name': 'Hum', 'position': 'right', 'offset': 60, 'axisLabel': {'color': '#32cd32'}, 'nameTextStyle': {'color': '#32cd32', 'padding': [0, 10, 0, 0]}, 'splitLine': {'show': False}},
                    {'show': False, 'type': 'value', 'name': 'Misc', 'position': 'right', 'offset': 120, 'axisLabel': {'color': '#ff69b4'}, 'nameTextStyle': {'color': '#ff69b4', 'padding': [0, 10, 0, 0]}, 'splitLine': {'show': False}},
                    {'show': False, 'type': 'value', 'min': 0, 'max': 1}  # Dedicated hidden Y-axis for bottom-aligned Events bar
                ],
                'series': [],
                'dataZoom': [{'type': 'inside'}, {'type': 'slider', 'bottom': '8%', 'height': 20}]
            }).classes('w-full h-[450px]')
            chart.on('click', on_chart_click)
        
        legend_container = ui.row().classes('w-full max-w-[1200px] mt-2 justify-center gap-4 flex-nowrap overflow-x-auto p-2')
        
        # Container for expandable event notices below the chart
        events_container = ui.column().classes('w-full max-w-[1200px] mt-4 gap-2')

        async def fetch_and_render():
            hrs = hours_select.value
            if hrs == 0:
                s_date = start_date_input.value
                e_date = end_date_input.value
                data = await data_logger.get_historical_data_async(hours_back=24, start_date=s_date, end_date=e_date)
            else:
                data = await data_logger.get_historical_data_async(hours_back=hrs)
            
            series_dict = {}
            last_ts_global = None
            port_valve_states = {}
            events = []
            
            # Dynamically derive offline gap threshold based on query window size to ignore downsampling strides
            gap_threshold = 65
            if hrs >= 720:
                gap_threshold = 4000
            elif hrs >= 168:
                gap_threshold = 1200
            elif hrs >= 24:
                gap_threshold = 300
            elif hrs == 0:
                gap_threshold = 1200
            
            # Group by Port & Metric, and detect events sequentially
            for row in data:
                ts = row['timestamp'] # SQlite timestamp string like "2024-03-05 10:00:00"
                # convert to JS timestamp format
                import datetime
                try:
                    dt = datetime.datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
                    js_ts = int(dt.timestamp() * 1000)
                except:
                    continue
                
                # Check global gap for potential system offline / power failure
                if last_ts_global is not None:
                    gap_seconds = (js_ts - last_ts_global) / 1000.0
                    # If the gap between consecutive logs exceeds the expected downsampled stride, log a unique offline recovery event
                    if gap_seconds > gap_threshold:
                        events.append({
                            'timestamp': js_ts,
                            'title': 'System Offline / Recovery',
                            'description': f'Telemetry gap of {int(gap_seconds)} seconds detected. System recovered from potential power failure or reboot.',
                            'type': 'power',
                            'color': '#ef4444' # Red
                        })
                last_ts_global = js_ts
                    
                port = row['port']
                s_type = row['sensor_type']
                metrics = row['data']
                
                port_name = settings.get(f"{port}_name", f"Port {port}")
                
                # Apply scaling mapped unit
                t_gp1, p_gp1, f_gp1 = get_effective_units(port)
                
                if "MP-F" in s_type or "MP-FN" in s_type:
                    # Check valve toggles
                    v_raw = metrics.get('1ValveState')
                    if v_raw is None:
                        v_raw = metrics.get('ValveState')
                        
                    if v_raw is not None:
                        v_state = bool(int(v_raw * 10.0)) if isinstance(v_raw, float) else bool(v_raw)
                        if port in port_valve_states:
                            if port_valve_states[port] != v_state:
                                state_str = "Opened" if v_state else "Closed"
                                color = "#10b981" if v_state else "#6b7280"
                                events.append({
                                    'timestamp': js_ts,
                                    'title': f'{port_name} Valve {state_str}',
                                    'description': f'MP-FN valve on {port_name} changed state to {"OPEN" if v_state else "CLOSED"}.',
                                    'type': f'valve_{"on" if v_state else "off"}',
                                    'color': color
                                })
                        port_valve_states[port] = v_state

                    # Flow (Axis 1 - Left Offset)
                    flow = apply_unit_scaling(metrics.get('1FlowInst', 0), 'flow', port)
                    flow_name = f"{port_name} Flow ({f_gp1})"
                    if flow_name not in series_dict: series_dict[flow_name] = {'name': flow_name, 'type': 'line', 'yAxisIndex': 1, 'data': [], 'showSymbol': False, 'smooth': True, 'port': port}
                    series_dict[flow_name]['data'].append([js_ts, round(flow, 2)])
                    
                    # Pressure (Axis 0 - Left Primary)
                    pres = apply_unit_scaling(metrics.get('1Pressure', 0), 'pres', port)
                    pres_name = f"{port_name} Pres ({p_gp1})"
                    if pres_name not in series_dict: series_dict[pres_name] = {'name': pres_name, 'type': 'line', 'yAxisIndex': 0, 'data': [], 'showSymbol': False, 'smooth': True, 'port': port}
                    series_dict[pres_name]['data'].append([js_ts, round(pres, 2)])
                    
                    # Temp (Axis 2 - Right Primary)
                    temp = apply_unit_scaling(metrics.get('1Temperature', 0) / 10.0, 'temp', port)
                    temp_name = f"{port_name} Temp ({t_gp1})"
                    if temp_name not in series_dict: series_dict[temp_name] = {'name': temp_name, 'type': 'line', 'yAxisIndex': 2, 'data': [], 'showSymbol': False, 'smooth': True, 'port': port}
                    series_dict[temp_name]['data'].append([js_ts, round(temp, 2)])

                    # Hum (Axis 3 - Right Offset)
                    hum = metrics.get('1Humidity', 0) / 10.0
                    hum_name = f"{port_name} Hum (%)"
                    if hum_name not in series_dict: series_dict[hum_name] = {'name': hum_name, 'type': 'line', 'yAxisIndex': 3, 'data': [], 'showSymbol': False, 'smooth': True, 'port': port}
                    series_dict[hum_name]['data'].append([js_ts, round(hum, 2)])
                    
                elif "GP-M" in s_type:
                    # Pressure (Axis 0 - Left Primary)
                    pres = apply_unit_scaling(metrics.get('Pressure', 0), 'pres', port)
                    pres_name = f"{port_name} Pres ({p_gp1})"
                    if pres_name not in series_dict: series_dict[pres_name] = {'name': pres_name, 'type': 'line', 'yAxisIndex': 0, 'data': [], 'showSymbol': False, 'smooth': True, 'port': port}
                    series_dict[pres_name]['data'].append([js_ts, round(pres, 2)])
                    
                    # Temp (Axis 2 - Right Primary)
                    temp = apply_unit_scaling(metrics.get('Temp', 0) / 10.0, 'temp', port)
                    temp_name = f"{port_name} Temp ({t_gp1})"
                    if temp_name not in series_dict: series_dict[temp_name] = {'name': temp_name, 'type': 'line', 'yAxisIndex': 2, 'data': [], 'showSymbol': False, 'smooth': True, 'port': port}
                    series_dict[temp_name]['data'].append([js_ts, round(temp, 2)])
                
                else:
                    # Catch-all Generic Fallback
                    # If we don't know what this sensor is, we will plot any numeric data
                    # on the 5th axis (Misc - Right Offset 120) and flag it visible
                    for key, val in metrics.items():
                        if isinstance(val, (int, float)):
                            generic_name = f"{port_name} {key}"
                            if generic_name not in series_dict: 
                                series_dict[generic_name] = {'name': generic_name, 'type': 'line', 'yAxisIndex': 4, 'data': [], 'showSymbol': False, 'smooth': True, 'port': port}
                                chart.options['yAxis'][4]['show'] = True
                            series_dict[generic_name]['data'].append([js_ts, round(val, 2)])
            
            # Formatting and rebuilding generic axis visibility state
            if not any(s['yAxisIndex'] == 4 for s in series_dict.values()):
                chart.options['yAxis'][4]['show'] = False
            
            # Update cache and prepare ECharts Events series
            current_events_cache.clear()
            current_events_cache.extend(events)
            
            event_series_data = []
            for ev in events:
                event_series_data.append({
                    'name': ev['title'],
                    'value': [ev['timestamp'], 0.05],
                    'itemStyle': {'color': ev['color']},
                    'symbol': 'path://M12,2A10,10 0 0,1 22,12A10,10 0 0,1 12,22A10,10 0 0,1 2,12A10,10 0 0,1 12,2M11,16.5L18,10H13L14,5.5L7,12H12L11,16.5Z' if ev['type'] == 'power' else 'circle',
                    'symbolSize': 16 if ev['type'] == 'power' else 14
                })
                
            events_series = {
                'name': 'Events',
                'type': 'scatter',
                'yAxisIndex': 5, # Map to our hidden [0, 1] min/max axis
                'data': event_series_data,
                'tooltip': {
                    'trigger': 'item',
                    'formatter': '<b>{b}</b><br/><span style="font-size:11px;color:#aaa">Click point for full details</span>'
                }
            }
            
            # Format for ECharts
            series_list = list(series_dict.values())
            
            # Tier-2 Protection: Ensure no individual series array exceeds CM4 display resolution (1280x800)
            for s in series_list:
                if 'data' in s and len(s['data']) > 350:
                    step_s = max(1, len(s['data']) // 350)
                    s['data'] = s['data'][::step_s]
                    
            if event_series_data:
                series_list.append(events_series)
                
            legend_data = [s['name'] for s in series_list]
            
            chart.options['legend']['data'] = legend_data
            chart.options['series'] = series_list
            # Default to showing all
            chart.options['legend']['selected'] = {name: True for name in legend_data}
            chart.update()
            
            # Rebuild Legend Container
            legend_container.clear()
            
            with legend_container:
                # Get unique ports that have data
                active_ports = sorted(list(set([s['port'] for s in series_list if 'port' in s])))
                
                # We need a state variable to track if we are currently isolating a sensor
                isolation_state = {'active_port': None}
                
                def on_sensor_click(clicked_port):
                    if isolation_state['active_port'] == clicked_port:
                        # Toggle off isolation: Show ALL
                        isolation_state['active_port'] = None
                        new_selected = {s['name']: True for s in series_list}
                    else:
                        # Isolate clicked port but keep Events visible
                        isolation_state['active_port'] = clicked_port
                        new_selected = {s['name']: (s.get('port') == clicked_port or s['name'] == 'Events') for s in series_list}
                        
                    chart.options['legend']['selected'] = new_selected
                    chart.update()

                # "All Sensors" Reset Button
                with ui.card().classes('cursor-pointer hover:bg-gray-800 transition-colors shrink-0 w-28 items-center flex flex-col p-2 bg-indigo-900 border border-indigo-500').on('click', lambda: on_sensor_click(None)):
                    with ui.element('div').classes('h-12 w-12 bg-white/10 rounded shadow-sm flex items-center justify-center'):
                        ui.icon('apps', size='1.8rem').classes('text-white drop-shadow-sm')
                    ui.label("Show All").classes('text-[10px] font-bold text-center mt-1 uppercase')

                for p in active_ports:
                    s_type = settings.get(str(p), "")
                    pic_path = sensor_parser.get_sensor_pic(s_type)
                    icon_path = sensor_parser.get_sensor_icon(s_type)

                    img_src = pic_path if pic_path else icon_path
                    p_name = settings.get(f"{p}_name", f"Port {p}")
                    
                    with ui.card().classes('cursor-pointer hover:bg-gray-800 transition-colors shrink-0 w-28 items-center flex flex-col p-2 bg-[#1a1c1e] border border-gray-700').on('click', lambda port=p: on_sensor_click(port)):
                        if img_src:
                            rel_src = f"/iodd_assets/{os.path.relpath(img_src, os.path.abspath(IODD_DIR))}"
                            ui.image(rel_src).classes('h-12 w-12 object-contain bg-white rounded shadow-sm q-pa-xs').props('fit="contain"')
                        ui.label(p_name).classes('text-[10px] font-bold text-center mt-1 truncate w-full')

            # Rebuild Expandable Event Notices list below chart
            events_container.clear()
            with events_container:
                if events:
                    with ui.expansion(f"Event Notices & Logs ({len(events)})", icon="history").classes('w-full bg-[#1a1c1e] rounded-lg border border-gray-800 font-bold').props('default-opened'):
                        with ui.column().classes('w-full q-pa-sm gap-2 max-h-60 overflow-y-auto font-normal'):
                            for ev in reversed(events):
                                with ui.expansion(ev['title'], icon='warning' if ev['type']=='power' else 'settings_input_component').classes('w-full bg-black/30 rounded border border-gray-800 text-sm').style(f'border-left: 4px solid {ev["color"]}'):
                                    import datetime
                                    dt_str = datetime.datetime.fromtimestamp(ev['timestamp']/1000.0).strftime('%Y-%m-%d %H:%M:%S')
                                    with ui.column().classes('q-pa-sm gap-1'):
                                        ui.label(f"Logged at: {dt_str}").classes('text-xs text-grey-4 font-mono')
                                        ui.label(ev['description']).classes('text-xs text-grey-2')
                else:
                    with ui.row().classes('w-full justify-center q-pa-sm bg-[#1a1c1e]/50 rounded border border-gray-800/50'):
                        ui.label("No event notices logged in this time window.").classes('text-xs text-grey-5')

        hours_select.on_value_change(fetch_and_render)

        def on_custom_date_picked():
            if hours_select.value != 0:
                hours_select.value = 0  # This automatically triggers fetch_and_render
            else:
                ui.timer(0.05, fetch_and_render, once=True)

        start_date_input.on('update:model-value', on_custom_date_picked)
        end_date_input.on('update:model-value', on_custom_date_picked)
        
        ui.timer(0.1, fetch_and_render, once=True)

        # Refresh chart automatically only when on the 1-hour window (15s interval) to save CM4 CPU
        async def auto_refresh_tick():
            if hours_select.value == 1:
                await fetch_and_render()

        ui.timer(15.0, auto_refresh_tick)
