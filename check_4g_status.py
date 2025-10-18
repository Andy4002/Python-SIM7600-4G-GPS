#!/usr/bin/env python3
import serial
import subprocess
import re

# ==== CONFIGURATION ====
MODEM_PORT = "/dev/ttyUSB2"  # Replace with your modem port
PING_TARGET = "8.8.8.8"
PING_COUNT = 5

# ==== FUNCTION TO GET SIGNAL STRENGTH ====
def get_signal_strength(port):
    try:
        ser = serial.Serial(port, 115200, timeout=2)
        ser.write(b'AT+CSQ\r')
        response = ser.read(100).decode()
        ser.close()
        match = re.search(r'\+CSQ: (\d+),(\d+)', response)
        if match:
            rssi = int(match.group(1))
            ber = int(match.group(2))
            return rssi, ber
    except Exception as e:
        print(f"Error reading modem: {e}")
    return None, None

# ==== FUNCTION TO GET PING LATENCY ====
def get_ping_latency(target, count):
    try:
        output = subprocess.check_output(['ping', '-c', str(count), target]).decode()
        match = re.search(r'avg = .*?/(\d+\.\d+)/', output)
        if match:
            avg_latency = float(match.group(1))
        else:
            # fallback: parse Linux ping output
            match = re.search(r'rtt min/avg/max/mdev = [\d.]+/([\d.]+)', output)
            avg_latency = float(match.group(1)) if match else None
        return avg_latency
    except Exception as e:
        print(f"Error pinging {target}: {e}")
        return None

# ==== ASSESS SIGNAL QUALITY ====
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

# ==== ASSESS LATENCY FOR REMOTE DESKTOP ====
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

# ==== MAIN SCRIPT ====
if __name__ == "__main__":
    print("Checking 4G signal strength...")
    rssi, ber = get_signal_strength(MODEM_PORT)
    print(f"RSSI: {rssi}, BER: {ber}")
    print(f"Signal Quality: {assess_signal(rssi)}")

    print(f"\nPinging {PING_TARGET} to check latency...")
    latency = get_ping_latency(PING_TARGET, PING_COUNT)
    if latency:
        print(f"Average Latency: {latency:.1f} ms")
    else:
        print("Ping failed.")
    print(f"Latency Assessment: {assess_latency(latency)}")
