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
        if protocol == '06': # TCP
            tcp_payload = ip_payload[40:]
            if len(tcp_payload) >= 40: # src port (4), dst port (4)
                src_port = int(tcp_payload[0:4], 16)
                dst_port = int(tcp_payload[4:8], 16)
                if src_port == 44818 or dst_port == 44818:
                    data = tcp_payload[40:] # header length is variable but simple assumption
                    if data:
                        print(f"TCP {src_port}->{dst_port}: {data}")

