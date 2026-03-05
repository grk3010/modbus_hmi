import asyncio
import os
from nicegui import ui, app

from shared_state import settings, modbus_client, opcua_client, data_logger, sensor_parser, IODD_DIR
import pages.dashboard
import pages.sensor
import pages.charts
import pages.config

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
    .interactive-element {
        transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
        filter: drop-shadow(0 4px 6px rgba(0,0,0,0.5));
    }
    .interactive-element:hover {
        transform: scale(1.15);
        filter: drop-shadow(0 0 15px rgba(32, 201, 151, 0.8));
        z-index: 100 !important;
    }
    .compressor-zone {
        border-radius: 20px;
        transition: all 0.3s;
        border: 2px solid transparent;
        background: radial-gradient(circle at center, rgba(255,255,255,0.1) 0%, transparent 60%);
        opacity: 0;
    }
    .compressor-zone:hover {
        opacity: 1;
        border: 2px solid #20c997;
        box-shadow: 0 0 30px rgba(32, 201, 151, 0.3) inset;
        cursor: pointer;
    }
    .live-badge {
        background: rgba(0,0,0,0.7);
        padding: 4px 8px;
        border-radius: 8px;
        font-size: 14px;
        font-weight: bold;
        color: #fff;
        border: 1px solid rgba(255,255,255,0.1);
        backdrop-filter: blur(4px);
    }
</style>
""", shared=True)

# Serve extracted images
os.makedirs(IODD_DIR, exist_ok=True)
app.add_static_files('/iodd_assets', os.path.abspath(IODD_DIR))

async def data_logging_loop():
    while True:
        try:
            is_enabled = settings.get("enable_logging", False)
            interval = float(settings.get("logging_interval", 10.0))
            if interval < 1.0: interval = 1.0

            if is_enabled:
                for port_str, product_id in settings.items():
                    if not port_str.isdigit() or not product_id:
                        continue
                        
                    port_num = int(port_str)
                    is_sim = settings.get("use_simulation", False)
                    data_to_log = None

                    if is_sim:
                        import random
                        if "MP-F" in product_id:
                            data_to_log = {
                                '1FlowInst': random.uniform(10, 500) * 10,
                                '1FlowTotal': random.uniform(100, 5000),
                                '1Pressure': random.uniform(50, 800),
                                '1Temperature': random.uniform(200, 800),
                                '1Humidity': random.uniform(300, 700)
                            }
                        elif "GP-M" in product_id:
                            data_to_log = {
                                'Pressure': random.uniform(0, 5000),
                                'Temp': random.uniform(200, 800)
                            }
                    else:
                        if modbus_client.port_status.get(port_num, False):
                            data_to_log = modbus_client.port_data.get(port_num, {})

                    if data_to_log:
                        await data_logger.log_data_async(port_num, product_id, data_to_log)
                        
            await asyncio.sleep(interval)
        except Exception as e:
            print(f"Logging loop error: {e}")
            await asyncio.sleep(5)

# Run the Modbus polling in the background when the app starts
app.on_startup(lambda: asyncio.create_task(data_logging_loop()))
app.on_startup(lambda: asyncio.create_task(modbus_client.poll_ports(settings, sensor_parser)))
if opcua_client:
    app.on_startup(lambda: asyncio.create_task(opcua_client.connect_and_poll()))

if __name__ in {"__main__", "__mp_main__"}:
    ui.run(port=8080, dark=True, title="Industrial HMI")
