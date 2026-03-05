import xml.etree.ElementTree as ET

tree = ET.parse('/home/pi/modbus_hmi/iodd_files/extracted_KEYENCE_MP-F_IO-Link_V1_0/KEYENCE_MP-F_IO-Link_V1_0/KEYENCE-MP-F80-20230410-IODD1.1.xml')
root = tree.getroot()

ns = {'iodd': 'http://www.io-link.com/IODD/2010/10'}

texts = {}
for text_item in root.findall('.//iodd:Text', ns):
    text_id = text_item.get('id')
    text_val = text_item.get('value')
    texts[text_id] = text_val
    if "external" in text_val.lower() or "input" in text_val.lower():
        print(f"Text Match {text_id}: {text_val}")

print("\n--- Process Data Out Bits ---")
pdout = root.find('.//iodd:ProcessDataOut', ns)
if pdout is not None:
    dt = pdout.find('./iodd:Datatype', ns)
    if dt is not None:
        for item in dt.findall('./iodd:RecordItem', ns):
            bit_offset = item.get('bitOffset')
            name_elem = item.find('./iodd:Name', ns)
            name_id = name_elem.get('textId') if name_elem is not None else "Unknown"
            print(f"Bit {bit_offset}: {texts.get(name_id, name_id)}")
            
            for single_val in item.findall('.//iodd:SingleValue', ns):
                val = single_val.get('value')
                v_name_elem = single_val.find('./iodd:Name', ns)
                v_name_id = v_name_elem.get('textId') if v_name_elem is not None else "Unknown"
                print(f"  Value {val}: {texts.get(v_name_id, v_name_id)}")
