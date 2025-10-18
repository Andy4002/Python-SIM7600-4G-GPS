#!/usr/bin/env python3
import serial
import subprocess
import re
import time

# ==== CONFIGURATION ====
MODEM_PORT = "/dev/ttyUSB2"  # Replace with your modem port
PING_TARGET = "8.8.8.8"
PING_COUNT = 3
CHECK_INTERVAL = 60  # seconds
MIN_RSSI = 15        # minimum RSSI to consider connection good
MAX_LATENCY = 120    # ms

# LTE bands to try (example: common in India)
LTE_BANDS = [40, 3, 5]  # adjust based on your provider

# ==== HELPER FUNCTIONS ====
def send_at_command(cmd):
    try:
        ser = serial.Serial(MODEM_PORT, 115200, timeout=2)
        ser.write((cmd + "\r").encode())
        response = ser.read(200).decode(errors='ignore')
        ser.close()
        return response
    except Exception as e:
        print(f"Error sending AT command: {e}")
        return None

def get_signal_strength():
    resp = send_at_command("AT+CSQ")
    if resp:
        match = re.search(r'\+CSQ: (\d+),(\d+)', resp)
        if match:
            rssi = int(match.group(1))
            ber = int(match.group(2))
            return rssi, ber
    return None, None

def assess_signal(rssi):
    if rssi is None:
        return "Unknown"
    if rssi < 10:
        return "Poor"
    elif rssi < 15:
        return "Fair"
    elif rssi < 20:
        return "Good"
    else:
        return "Excellent"

def get_ping_latency():
    try:
        output = subprocess.check_output(['ping', '-c', str(PING_COUNT), PING_TARGET]).decode()
        match = re.search(r'rtt min/avg/max/mdev = [\d.]+/([\d.]+)', output)
        if match:
            return float(match.group(1))
    except Exception as e:
        print(f"Ping failed: {e}")
    return None

def assess_latency(latency):
    if latency is None:
        return "Unknown"
    if latency < 60:
        return "Excellent for remote desktop"
    elif latency < 120:
        return "Good, slight lag possible"
    elif latency < 200:
        return "Usable, noticeable lag"
    else:
        return "Poor, not recommended"

def reconnect_modem():
    print("Attempting to reconnect modem...")
    send_at_command("AT+CFUN=0")  # disable modem
    time.sleep(3)
    send_at_command("AT+CFUN=1")  # enable modem
    time.sleep(5)
    print("Modem reconnected.")

def switch_lte_band(band):
    print(f"Switching LTE band to {band}...")
    send_at_command(f"AT+CBAND={band}")
    time.sleep(5)

# ==== MAIN MONITOR LOOP ====
if __name__ == "__main__":
    print("Starting 4G monitor... Press Ctrl+C to stop.")
    while True:
        rssi, ber = get_signal_strength()
        latency = get_ping_latency()

        print(f"\nSignal: RSSI={rssi}, BER={ber}, Quality={assess_signal(rssi)}")
        print(f"Latency: {latency} ms, Assessment={assess_latency(latency)}")

        # Check thresholds
        if rssi is None or rssi < MIN_RSSI or (latency is not None and latency > MAX_LATENCY):
            print("Signal or latency below threshold. Attempting recovery...")
            reconnect_modem()
            # Try switching bands
            for band in LTE_BANDS:
                switch_lte_band(band)
                time.sleep(10)
                rssi_check, _ = get_signal_strength()
                if rssi_check and rssi_check >= MIN_RSSI:
                    print(f"Signal restored on band {band}.")
                    break
            else:
                print("Unable to restore strong signal. Will retry in next interval.")

        time.sleep(CHECK_INTERVAL)
