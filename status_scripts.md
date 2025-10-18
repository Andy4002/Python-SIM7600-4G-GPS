
# **Documentation for 4G Monitoring/Status Scripts**

## **1. Script: `check_4g_status.py`**

### **Purpose**

* Provides a **quick snapshot** of your SIM7600G-H 4G modem’s status.
* Reads **signal strength** (RSSI & BER) and **ping latency**.
* Gives a **human-readable assessment** for remote desktop usage.

---

### **Requirements**

* **Python 3**
* Libraries: `serial` (pySerial)
* Access to the modem’s USB port (e.g., `/dev/ttyUSB2`)
* Internet access for ping test

---

### **Setup**

1. Install dependencies:

```bash
sudo apt update
sudo apt install python3-pip
pip3 install pyserial
```

2. Identify your modem USB port:

```bash
dmesg | grep tty
```

3. Edit `MODEM_PORT` in the script to match your modem device.

---

### **Configuration Variables**

| Variable      | Purpose                               |
| ------------- | ------------------------------------- |
| `MODEM_PORT`  | The `/dev/ttyUSBx` path to the modem  |
| `PING_TARGET` | IP address to ping (default: 8.8.8.8) |
| `PING_COUNT`  | Number of ping packets to send        |

---

### **How It Works**

1. Opens the modem serial port and sends AT command `AT+CSQ`.
2. Parses RSSI (signal strength) and BER (bit error rate).
3. Pings `PING_TARGET` to calculate average latency.
4. Assesses:

   * Signal quality: Poor / Fair / Good / Excellent
   * Latency for remote desktop: Excellent / Good / Usable / Poor

---

### **Usage**

```bash
sudo chmod +x check_4g_status.py
sudo ./check_4g_status.py
```

### **Sample Output**

```
Checking 4G signal strength...
RSSI: 29, BER: 99
Signal Quality: Excellent

Pinging 8.8.8.8 to check latency...
Average Latency: 42.5 ms
Latency Assessment: Excellent for remote desktop
```

---

## **2. Script: `monitor_4g_status.py`**

### **Purpose**

* **Continuous monitoring** of your SIM7600G-H 4G modem.
* Automatically attempts **recovery** if signal or latency drops.
* Can **reconnect the modem** and **switch LTE bands**.
* Keeps connection **ready for remote desktop**.

---

### **Requirements**

* Python 3
* Libraries: `serial` (pySerial)
* Modem USB access
* Optional: Knowledge of LTE bands your SIM supports

---

### **Setup**

1. Install dependencies:

```bash
sudo apt update
sudo apt install python3-pip
pip3 install pyserial
```

2. Identify your modem USB port:

```bash
dmesg | grep tty
```

3. Configure:

   * `MODEM_PORT` → your modem device (`/dev/ttyUSBx`)
   * `PING_TARGET` → IP to ping (default: 8.8.8.8)
   * `CHECK_INTERVAL` → seconds between checks
   * `MIN_RSSI` → minimum RSSI to consider connection good
   * `MAX_LATENCY` → max latency for acceptable remote desktop
   * `LTE_BANDS` → list of LTE bands to try in case of poor signal

---

### **Configuration Variables**

| Variable         | Purpose                                    |
| ---------------- | ------------------------------------------ |
| `MODEM_PORT`     | USB port of the modem                      |
| `PING_TARGET`    | IP address to ping                         |
| `PING_COUNT`     | Number of ping packets                     |
| `CHECK_INTERVAL` | How often (seconds) to check status        |
| `MIN_RSSI`       | Minimum RSSI for good signal               |
| `MAX_LATENCY`    | Maximum acceptable latency (ms)            |
| `LTE_BANDS`      | LTE bands to attempt if connection is poor |

---

### **How It Works**

1. Reads **RSSI & BER** from the modem using AT+CSQ.
2. Measures **ping latency** to a target server.
3. Assesses:

   * Signal quality (Poor → Excellent)
   * Latency for remote desktop (Poor → Excellent)
4. If thresholds are not met:

   * Reconnects the modem using `AT+CFUN=0` / `AT+CFUN=1`
   * Cycles through LTE bands using `AT+CBAND=<band>` until signal improves
5. Waits `CHECK_INTERVAL` seconds and repeats.

---

### **Usage**

```bash
sudo chmod +x monitor_4g_connection.py
sudo ./monitor_4g_connection.py
```

---

### **Sample Output**

```
Starting 4G monitor... Press Ctrl+C to stop.

Signal: RSSI=29, BER=99, Quality=Excellent
Latency: 42.3 ms, Assessment=Excellent for remote desktop

Signal: RSSI=8, BER=99, Quality=Poor
Latency: 210 ms, Assessment=Poor, not recommended
Signal or latency below threshold. Attempting recovery...
Attempting to reconnect modem...
Switching LTE band to 40...
Signal restored on band 40.
```

---

### **Notes**

* The script is **self-healing**: reconnects and tries different LTE bands automatically.
* Can be run as a **systemd service** to monitor continuously in the background.
* Works best if you know **which LTE bands your carrier supports**.
