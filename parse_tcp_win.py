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
        
        if '172.16.1.32' in [src_ip, dst_ip] and protocol == '06': # TCP
            tcp_payload = ip_payload[40:]
            if len(tcp_payload) >= 40:
                data = tcp_payload[40:]
                print(f"TCP {src_ip}->{dst_ip}: {data}")

