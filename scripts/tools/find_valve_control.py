import xml.etree.ElementTree as ET

tree = ET.parse('/home/pi/modbus_hmi/iodd_files/extracted_KEYENCE_MP-F_IO-Link_V1_0/KEYENCE_MP-F_IO-Link_V1_0/KEYENCE-MP-F80-20230410-IODD1.1.xml')
root = tree.getroot()

ns = {'iodd': 'http://www.io-link.com/IODD/2010/10'}

texts = {}
for text_item in root.findall('.//iodd:Text', ns):
    texts[text_item.get('id')] = text_item.get('value')

print("--- Variables with 'rw' or 'wo' ---")
for var in root.findall('.//iodd:Variable', ns):
    access = var.get('accessRights')
    if access in ['rw', 'wo']:
        idx = var.get('index')
        name_elem = var.find('./iodd:Name', ns)
        name_id = name_elem.get('textId') if name_elem is not None else "Unknown"
        english_name = texts.get(name_id, name_id)
        print(f"Index {idx} ({access}): {english_name}")

print("\n--- System Commands ---")
for btn in root.findall('.//iodd:Button', ns):
    val = btn.get('buttonValue')
    desc = btn.find('./iodd:Description', ns)
    desc_id = desc.get('textId') if desc is not None else "Unknown"
    english_name = texts.get(desc_id, desc_id)
    print(f"Button {val}: {english_name}")

