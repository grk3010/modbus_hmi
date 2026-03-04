import asyncio
from asyncua import Client

class OpcUaClient:
    def __init__(self, settings_ref):
        self.settings = settings_ref
        self.client = None
        self.connected = False
        self.data = {
            "pressure": 0.0,
            "temperature": 0.0,
            "running_hours": 0.0,
            "running": False
        }
    
    async def connect_and_poll(self):
        while True:
            ip = self.settings.get("opcua_ip", "")
            if not ip:
                await asyncio.sleep(5)
                continue
                
            url = f"opc.tcp://{ip}:4840"
            if not self.client or self.client.server_url.geturl() != url:
                if self.client:
                    try:
                        await self.client.disconnect()
                    except:
                        pass
                self.client = Client(url=url)
            
            try:
                if not self.connected:
                    await self.client.connect()
                    self.connected = True
                
                # Mock nodes for now or attempt to read if user configured them
                pressure_node = self.settings.get("opcua_node_pressure", "")
                temp_node = self.settings.get("opcua_node_temp", "")
                hours_node = self.settings.get("opcua_node_hours", "")
                state_node = self.settings.get("opcua_node_state", "")
                
                if pressure_node:
                    node = self.client.get_node(pressure_node)
                    self.data["pressure"] = await node.read_value()
                else:
                    self.data["pressure"] = 120.5  # mock
                    
                if temp_node:
                    node = self.client.get_node(temp_node)
                    self.data["temperature"] = await node.read_value()
                else:
                    self.data["temperature"] = 85.2 # mock
                    
                if hours_node:
                    node = self.client.get_node(hours_node)
                    self.data["running_hours"] = await node.read_value()
                else:
                    self.data["running_hours"] = 1234.5 # mock
                    
                if state_node:
                    node = self.client.get_node(state_node)
                    self.data["running"] = await node.read_value()
                else:
                    # just toggle randomly for mock
                    pass
                    
            except Exception as e:
                self.connected = False
                print(f"OPC UA Error: {e}")
                await asyncio.sleep(5)
            
            await asyncio.sleep(1.0)
            
    async def start_compressor(self):
        if not self.connected or not self.client: return
        start_node = self.settings.get("opcua_node_start", "")
        if start_node:
            try:
                node = self.client.get_node(start_node)
                # Atlas copco start is usually setting a bool node
                from asyncua import ua
                await node.write_value(ua.DataValue(ua.Variant(True, ua.VariantType.Boolean)))
            except Exception as e:
                print(f"Failed to start compressor: {e}")

    async def stop_compressor(self):
        if not self.connected or not self.client: return
        stop_node = self.settings.get("opcua_node_stop", "")
        if stop_node:
            try:
                node = self.client.get_node(stop_node)
                from asyncua import ua
                await node.write_value(ua.DataValue(ua.Variant(True, ua.VariantType.Boolean)))
            except Exception as e:
                print(f"Failed to stop compressor: {e}")
