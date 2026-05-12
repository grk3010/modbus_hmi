#!/usr/bin/env python3
import time
import logging
import subprocess
import os
try:
    from gpiozero import DigitalInputDevice
except ImportError:
    print("gpiozero not installed. Run: sudo apt-get install python3-gpiozero")
    exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Configuration
DI_PIN = 16  # CM4 GPIO 16 (DI1 on reTerminal DM)
DELAY_SECONDS = 5  # Increased to 5s to ignore industrial noise/voltage dips
# We use pull_up=True because the UPS is an Open Collector (floating when good)
PULL_UP = True 

logging.info(f"Starting UPS Monitor on GPIO {DI_PIN}")
logging.info(f"NORMAL State: Pin is HIGH (1)")
logging.info(f"POWER FAIL State: Pin goes LOW (0)")

# Initialize the GPIO pin
# Logic: pull_up=True ensures the pin is 1 unless the UPS pulls it to ground (0)
ups_pin = DigitalInputDevice(DI_PIN, pull_up=PULL_UP)

def recovery_reboot():
    logging.critical("Initiating safe reboot cycle now!")
    # CRITICAL: Flush filesystem buffers to protect your compressor logs/configs
    os.system("sync")
    time.sleep(2)
    # Execute reboot
    subprocess.run(['sudo', 'reboot'])

# Main loop
power_fail_start_time = None

try:
    while True:
        # NEW LOGIC: 
        # ups_pin.value == 0 means the UPS has grounded the pin (Power Failed)
        # ups_pin.value == 1 means the UPS is open (Power is Good)
        if ups_pin.value == 0:
            if power_fail_start_time is None:
                power_fail_start_time = time.time()
                logging.warning("Power failure detected! Waiting to verify...")
            else:
                elapsed = time.time() - power_fail_start_time
                if elapsed >= DELAY_SECONDS:
                    logging.critical(f"Power failure confirmed for {DELAY_SECONDS}s. Rebooting.")
                    recovery_reboot()
                    time.sleep(60) 
        else:
            if power_fail_start_time is not None:
                logging.info("Power restored. Shutdown sequence aborted.")
                power_fail_start_time = None
        
        time.sleep(0.1)
except KeyboardInterrupt:
    logging.info("UPS Monitor stopped by user.")
except Exception as e:
    logging.error(f"UPS Monitor error: {e}")