import os
import glob
import json
import xml.etree.ElementTree as ET
import zipfile

class SensorParser:
    def __init__(self, iodd_dir="/home/pi/modbus_hmi/iodd_files"):
        self.iodd_dir = iodd_dir
        self.sensors = {} # {product_id: {variables}}
        self.icons = {} # {product_id: icon_path}
        self.pics = {} # {product_id: pic_path}
        self.device_id_map = {} # {(vendor_id, device_id): product_id}
        self._extract_all()
        self._parse_all()

    def _extract_all(self):
        """Extract all zip files in the IODD directory."""
        for zip_file in glob.glob(os.path.join(self.iodd_dir, "*.zip")):
            folder_name = os.path.splitext(os.path.basename(zip_file))[0]
            extract_path = os.path.join(self.iodd_dir, f"extracted_{folder_name}")
            if not os.path.exists(extract_path):
                print(f"Extracting {zip_file}...")
                with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                    zip_ref.extractall(extract_path)

    def _parse_all(self):
        """Find and parse all IODD XML files."""
        for root, dirs, files in os.walk(self.iodd_dir):
            for file in files:
                if file.endswith("IODD1.1.xml"):
                    xml_path = os.path.join(root, file)
                    self._parse_xml(xml_path)

    def _parse_xml(self, xml_path):
        """Parse a single IODD XML file for ProcessDataIn and device identify."""
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            
            # Extract namespace
            ns = {'io': 'http://www.io-link.com/IODD/2010/10'}

            # Find Product IDs
            identity_node = root.find('.//io:DeviceIdentity', ns)
            if identity_node is None:
                return
            
            vendor_id = int(identity_node.get('vendorId', '0'))
            device_id = int(identity_node.get('deviceId', '0'))
            
            # Build text dictionary
            text_dict = self._get_text_dict(root, ns)
            
            product_ids = []
            icons_map = {}
            pics_map = {}
            for variant in identity_node.findall('.//io:DeviceVariant', ns):
                pid = variant.get('productId')
                icon = variant.get('deviceIcon')
                pic = variant.get('deviceSymbol')
                if pid:
                    product_ids.append(pid)
                    if icon:
                        icons_map[pid] = os.path.join(os.path.dirname(xml_path), icon)
                    if pic:
                        pics_map[pid] = os.path.join(os.path.dirname(xml_path), pic)

            if not product_ids:
                return

            if vendor_id and device_id and product_ids:
                # Map the primary product ID to this vendor/device combo
                self.device_id_map[(vendor_id, device_id)] = product_ids[0]

            # Extract ProcessDataIn variables
            process_data = {}
            pd_in = root.find('.//io:ProcessDataIn', ns)
            
            if pd_in is not None:
                for item in pd_in.findall('.//io:RecordItem', ns):
                    name_node = item.find('io:Name', ns)
                    text_id = name_node.get('textId') if name_node is not None else "Unknown"
                    raw_name = text_dict.get(text_id, "Unknown")
                    
                    # 1. Original simplified ID key (e.g. 1FlowInst)
                    clean_id = text_id.replace("TI_PDIn", "").replace("TI_PD_ProcessData", "ProcessData")
                    # 2. New descriptive key (e.g. InstantaneousFlow)
                    clean_name = raw_name.replace(" ", "").replace("_", "")
                    
                    bit_offset = item.get('bitOffset')
                    
                    datatype_node = item.find('io:SimpleDatatype', ns)
                    datatype = "Unknown"
                    bit_length = "1"
                    
                    if datatype_node is not None:
                        datatype = datatype_node.get('{http://www.w3.org/2001/XMLSchema-instance}type')
                        bit_length = datatype_node.get('bitLength', '1')
                    
                    if bit_offset is not None:
                        meta = {
                            "bit_offset": int(bit_offset),
                            "bit_length": int(bit_length),
                            "datatype": datatype,
                            "display_name": raw_name,
                            "native_unit": self._guess_unit(raw_name)
                        }
                        process_data[clean_id] = meta
                        if clean_name != clean_id:
                            process_data[clean_name] = meta
                    else:
                        print(f"Skipping {raw_name} due to missing bitOffset")

            # Map the parsed data to all product IDs found in this file
            for pid in product_ids:
                self.sensors[pid] = process_data
                if pid in icons_map:
                    self.icons[pid] = icons_map[pid]
                if pid in pics_map:
                    self.pics[pid] = pics_map[pid]

        except Exception as e:
            print(f"Error parsing XML {xml_path}: {e}")

    def _get_text_dict(self, root, ns):
        """Extract all text translations from the IODD."""
        texts = {}
        for text_node in root.findall('.//io:ExternalTextCollection/io:PrimaryLanguage/io:Text', ns):
            text_id = text_node.get('id')
            value = text_node.get('value')
            if text_id and value:
                texts[text_id] = value
        return texts

    def _guess_unit(self, name):
        """Guess the native unit based on the parameter name (Common for Keyence)."""
        n = name.lower()
        if "pressure" in n:
            return "kPa"
        if "flow" in n:
            return "L/min"
        if "temp" in n or "temperature" in n:
            return "°C"
        if "humidity" in n:
            return "%"
        return None

    def get_available_sensors(self):
        """Return a list of available sensor Product IDs."""
        return list(self.sensors.keys())

    def get_sensor_map(self, product_id):
        """Return the parsing map for a specific sensor."""
        return self.sensors.get(product_id, {})

    def get_product_by_id(self, vendor_id, device_id):
        """Returns the product_id string (if found) for the given IO-Link IDs."""
        return self.device_id_map.get((vendor_id, device_id))

    def get_sensor_icon(self, product_id):
        """Return the absolute path to the sensor icon."""
        return self.icons.get(product_id)

    def get_sensor_pic(self, product_id):
        """Return the absolute path to the sensor picture."""
        return self.pics.get(product_id)

if __name__ == "__main__":
    parser = SensorParser()
    print("Available Sensors:", parser.get_available_sensors())
    
    for pid in ["MP-FR80/MP-FG80/MP-FN80", "GP-M010T"]:
        s_map = parser.get_sensor_map(pid)
        print(f"\n{pid} Map ({len(s_map)} vars):")
        for k, v in list(s_map.items())[:5]:
            print(f"  {k}: {v.get('native_unit')} ({v.get('display_name')})")
