from nicegui import ui
import os
from shared_state import settings, data_logger, sensor_parser, IODD_DIR, get_effective_units, apply_unit_scaling

@ui.page('/charts')
def charts_page():
    with ui.header().classes('bg-dark text-white items-center q-pa-md shadow-2'):
        ui.button(icon='arrow_back', on_click=lambda: ui.navigate.to('/')).props('flat')
        ui.label('Historical Data Charts').classes('text-h5 font-bold')
        ui.space()
        
    with ui.column().classes('w-full q-pa-md items-center'):
        controls_card = ui.card().classes('w-full max-w-[1200px] mb-4 bg-dark text-white p-4')
        with controls_card:
            with ui.row().classes('w-full justify-between items-center'):
                with ui.row().classes('items-center gap-4'):
                    ui.label("Time Window:").classes('text-bold')
                    hours_select = ui.select({1: 'Last 1 Hour', 6: 'Last 6 Hours', 24: 'Last 24 Hours'}, value=1).classes('w-48')
                
                # Check logging status and display banner if off
                if not settings.get("enable_logging", False):
                    with ui.row().classes('items-center gap-2 bg-red-900/50 text-red-200 p-2 rounded border border-red-700'):
                        ui.icon('warning', size='sm')
                        ui.label("Local Logging is currently disabled.")
                        ui.button("Enable in Config", on_click=lambda: ui.navigate.to('/config')).props('flat size=sm').classes('ml-2 text-white')

        chart_card = ui.card().classes('w-full max-w-[1200px] bg-dark text-white p-4')
        
        # We will populate the options dynamically
        chart = ui.echart({
            'tooltip': {'trigger': 'axis'},
            'legend': {'data': [], 'textStyle': {'color': '#ccc'}, 'bottom': 0},
            'grid': {'left': '5%', 'right': '5%', 'bottom': '15%', 'containLabel': True},
            'xAxis': {'type': 'time', 'splitLine': {'show': False}, 'axisLabel': {'color': '#ccc'}},
            'yAxis': [
                {'type': 'value', 'name': 'Pressure', 'position': 'left', 'offset': 0, 'axisLabel': {'color': '#ffd700'}, 'nameTextStyle': {'color': '#ffd700'}, 'splitLine': {'lineStyle': {'color': '#333'}}},
                {'type': 'value', 'name': 'Flow', 'position': 'left', 'offset': 60, 'axisLabel': {'color': '#00ffff'}, 'nameTextStyle': {'color': '#00ffff'}, 'splitLine': {'show': False}},
                {'type': 'value', 'name': 'Temp', 'position': 'right', 'offset': 0, 'axisLabel': {'color': '#ff4500'}, 'nameTextStyle': {'color': '#ff4500'}, 'splitLine': {'show': False}},
                {'type': 'value', 'name': 'Humidity', 'position': 'right', 'offset': 60, 'axisLabel': {'color': '#32cd32'}, 'nameTextStyle': {'color': '#32cd32'}, 'splitLine': {'show': False}},
                {'show': False, 'type': 'value', 'name': 'Misc', 'position': 'right', 'offset': 120, 'axisLabel': {'color': '#ff69b4'}, 'nameTextStyle': {'color': '#ff69b4'}, 'splitLine': {'show': False}}
            ],
            'series': [],
            'dataZoom': [{'type': 'inside'}, {'type': 'slider', 'bottom': '5%'}]
        }).classes('w-full h-[600px]')
        
        legend_container = ui.row().classes('w-full max-w-[1200px] mt-8 justify-center gap-4 flex-wrap')
        
        async def fetch_and_render():
            hrs = hours_select.value
            data = await data_logger.get_historical_data_async(hours_back=hrs)
            
            series_dict = {}
            # Group by Port & Metric
            for row in data:
                ts = row['timestamp'] # SQlite timestamp string like "2024-03-05 10:00:00"
                # convert to JS timestamp format
                import datetime
                try:
                    dt = datetime.datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
                    js_ts = int(dt.timestamp() * 1000)
                except:
                    continue
                    
                port = row['port']
                s_type = row['sensor_type']
                metrics = row['data']
                
                port_name = settings.get(f"{port}_name", f"Port {port}")
                
                # Apply scaling mapped unit
                t_gp1, p_gp1, f_gp1 = get_effective_units(port)
                
                if "MP-F" in s_type:
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
            
            # Format for ECharts
            series_list = list(series_dict.values())
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
                active_ports = list(set([s['port'] for s in series_list]))
                
                # We need a state variable to track if we are currently isolating a sensor
                isolation_state = {'active_port': None}
                
                def on_sensor_click(clicked_port):
                    if isolation_state['active_port'] == clicked_port:
                        # Toggle off isolation: Show ALL
                        isolation_state['active_port'] = None
                        new_selected = {s['name']: True for s in series_list}
                    else:
                        # Isolate clicked port
                        isolation_state['active_port'] = clicked_port
                        new_selected = {s['name']: (s['port'] == clicked_port) for s in series_list}
                        
                    chart.options['legend']['selected'] = new_selected
                    chart.update()

                # "All Sensors" Reset Button
                with ui.card().classes('cursor-pointer hover:bg-gray-800 transition-colors w-32 items-center flex flex-col p-2 bg-indigo-900 border border-indigo-500').on('click', lambda: on_sensor_click(None)):
                    with ui.element('div').classes('h-16 w-16 bg-white/10 rounded shadow-sm q-pa-sm flex items-center justify-center'):
                        ui.icon('apps', size='2.5rem').classes('text-white drop-shadow-sm')
                    ui.label("Show All").classes('text-xs font-bold text-center mt-2')

                for p in active_ports:
                    s_type = settings.get(str(p), "")
                    pic_path = sensor_parser.get_sensor_pic(s_type)
                    icon_path = sensor_parser.get_sensor_icon(s_type)

                    img_src = pic_path if pic_path else icon_path
                    p_name = settings.get(f"{p}_name", f"Port {p}")
                    
                    with ui.card().classes('cursor-pointer hover:bg-gray-800 transition-colors w-32 items-center flex flex-col p-2').on('click', lambda port=p: on_sensor_click(port)):
                        if img_src:
                            rel_src = f"/iodd_assets/{os.path.relpath(img_src, os.path.abspath(IODD_DIR))}"
                            ui.image(rel_src).classes('h-16 w-16 object-contain bg-white rounded shadow-sm q-pa-sm').props('fit="contain"')
                        ui.label(p_name).classes('text-xs font-bold text-center mt-2')

        hours_select.on_value_change(fetch_and_render)
        ui.timer(0.1, fetch_and_render, once=True)
        # Refresh chart every 10 seconds while on page
        ui.timer(10.0, fetch_and_render)
