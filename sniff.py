import socket
import os
import time

s = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.ntohs(3))
s.bind(('eth0', 0))

print("Listening on eth0 for 10 seconds...")
start = time.time()
with open("dump.hex", "w") as f:
    while time.time() - start < 10:
        raw_data, addr = s.recvfrom(65535)
        f.write(raw_data.hex() + "\n")
print("Done")
