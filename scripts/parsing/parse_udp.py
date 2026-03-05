import binascii

with open('dump.hex') as f:
    lines = f.readlines()

for line in lines:
    line = line.strip()
    if len(line) < 28: continue
    
    eth_type = line[24:28]
    if eth_type == '0800': # IPv4
        ip_payload = line[28:]
        if len(ip_payload) < 40: continue
        
        protocol = ip_payload[18:20]
        src_ip = ".".join([str(int(ip_payload[24:26], 16)), str(int(ip_payload[26:28], 16)), str(int(ip_payload[28:30], 16)), str(int(ip_payload[30:32], 16))])
        dst_ip = ".".join([str(int(ip_payload[32:34], 16)), str(int(ip_payload[34:36], 16)), str(int(ip_payload[36:38], 16)), str(int(ip_payload[38:40], 16))])
        
        if protocol == '11': # UDP
            udp_payload = ip_payload[40:]
            if len(udp_payload) >= 16:
                src_port = int(udp_payload[0:4], 16)
                dst_port = int(udp_payload[4:8], 16)
                data = udp_payload[16:]
                print(f"UDP {src_ip}:{src_port} -> {dst_ip}:{dst_port} | {data}")

