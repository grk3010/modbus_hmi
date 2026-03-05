# Keyence IO-Link Modbus HMI Dashboard

An asynchronous, highly interactive web dashboard mapped over Modbus TCP for monitoring IO-Link industrial sensors in real time and visualizing their history.

## Environment Architecture

**1. `main.py` (Core Dashboard Entrypoint)**
Contains the NiceGUI application. Serves the web interface, the interactive polling map, the configuration page, and manages user views (such as the data visualization charts).

To start the dashboard locally:
```bash
# Optional but highly recommended: Activate the project virtual environment
source .venv/bin/activate 

python main.py
```

**2. Core Modules**
*   **`modbus_client.py`:** A dedicated asyncio handler wrapper used to poll real-time sensor register data. It dynamically decodes multi-byte CIP block offsets.
*   **`data_logger.py`:** An SQLite caching module that automatically stores data from configured sensors alongside chronological timestamps. This data facilitates `/charts` analytics.
*   **`opcua_client.py`:** An optional extension for communicating over OPC-UA infrastructure (such as standard compressors).

## Developer & Auxiliary Scripts
To keep the primary code uncluttered, numerous development and sandbox utilities have been categorized into sub-folders under `scripts/`.

**A. `scripts/parsing`**
Contains the `sensor_parser.py` module responsible for recursively extracting `.zip` metadata, unpacking IODD structural payload schema, scaling configuration logic, and resolving vendor/device names directly to visual thumbnails and text models within the application UI.

**B. `scripts/tools`**
Contains active standalone utility scripts that are extremely useful during device configuration or testing, but NOT part of the runtime dashboard loop:
*   `discover.py`, `scan_modbus.py` - Network pingers mapping available IO-Link Master controllers.
*   `sniff.py` - Low-level traffic capture parsing.
*   `find_valve_control.py` - Helper mapping ISDU IO logic.

**C. `scripts/tests`** 
Regression sandbox scripts testing protocol translations, string parsing, logic gates (`test_eip.py`, `test_mpf_payload.py`, etc.).

**D. `scripts/docs_and_logs`**
Raw dump dumps, static system manuals, HEX block captures, and text architecture notes representing reference datasets mapped out during platform conception.
