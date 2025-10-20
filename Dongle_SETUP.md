
# SIM7600G-H and RPI 5 setup for QMI/MBIM mode

**Complete, detailed documentation** covering everything we did to get SIM7600G-H USB dongle working in **QMI mode** on Raspberry Pi OS, including boot-time automation, DNS handling, IP assignment, and troubleshooting notes.

---

# SIM7600G-H QMI Setup Documentation on Raspberry Pi OS

## 1. **Overview**

This guide details setting up a SIM7600G-H 4G LTE USB modem to work in **QMI mode** on a Raspberry Pi running Raspberry Pi OS. It handles:

* Switching the modem to QMI mode (if not already)
* Detecting the modem device
* Configuring APN for any SIM
* Bringing up `wwan0` automatically at boot
* Assigning IP and routes
* Setting DNS safely, avoiding overwrites by NetworkManager
* Retrying connection if modem is slow to initialize

By following this guide, the system will automatically get internet access via 4G at boot.

---

## 2. **Initial Hardware and System Check**

1. **Connect the SIM7600G-H dongle** to a Raspberry Pi USB port.
2. Check USB devices:

```bash
lsusb
```

You should see an entry similar to:

```
Bus 001 Device 004: ID 1e0e:9001 SIMCom Wireless
```

3. Check kernel messages for QMI devices:

```bash
dmesg | grep -i qmi
```

Expected output:

```
qmi_wwan 1-2:1.5: cdc-wdm0: USB WDM device
qmi_wwan 1-2:1.5 wwan0: register 'qmi_wwan' at ...
```

If `wwan0` does not exist or modem is in **MBIM/AT mode**, you need to switch it to QMI.

---

## 3. **Switching SIM7600G-H to QMI Mode**

1. Install `usb-modeswitch` and QMI tools:

```bash
sudo apt update
sudo apt install usb-modeswitch libqmi-utils udhcpc -y
```

2. Verify the device modes:

```bash
ls /dev/cdc-wdm*
```

If empty or modem still not QMI, you may need to switch using AT commands via serial port:

```bash
sudo minicom -D /dev/ttyUSB2
# or
sudo screen /dev/ttyUSB2 115200
```

Send:

```
AT+QCFG="usbnet",1
```

Then **replug** the modem.

---

## 4. **Prevent ModemManager from interfering**

Network managers often block QMI modems. Create a **blacklist for ModemManager**:

```bash
sudo mkdir -p /etc/ModemManager/conf.d
sudo tee /etc/ModemManager/conf.d/99-ignore-sim7600.conf > /dev/null << 'EOF'
[filter]
# Ignore all SIMCom QMI devices
udev-property-match=ID_VENDOR_ID=1e0e
udev-property-match=ID_MODEL_ID=9001
EOF
```

Then reload ModemManager:

```bash
sudo systemctl restart ModemManager
```

---

## 5. **Create QMI Network Profile**

Create a QMI network configuration file:

```bash
sudo tee /etc/qmi-network.conf > /dev/null << 'EOF'
APN=YOUR_APN_HERE
APN_USER=unset
APN_PASS=unset
qmi-proxy=yes
IP_TYPE=4
PROFILE=unset
EOF
```

> Replace `YOUR_APN_HERE` with the APN of your SIM operator. If unknown, check SIM documentation or carrier website.

---

## 6. **Create QMI Autoconnect Script**

To automate boot-time connection:

```bash
sudo tee /usr/local/bin/qmi-autoconnect.sh > /dev/null << 'EOF'
#!/bin/bash
# qmi-autoconnect.sh - robust QMI start + DHCP for SIM7600G-H
set -euo pipefail
logger -t qmi-autoconnect "Starting qmi-autoconnect"

# Auto-detect first QMI device
QMI_DEV=$(ls /dev/cdc-wdm* | head -n1)
IFACE="wwan0"
DNS_FILE="/etc/resolv.conf"
DNS1="8.8.8.8"
DNS2="1.1.1.1"

# Check if wlan0 has IPv4
wlan_has_ipv4() { ip -4 addr show dev wlan0 2>/dev/null | grep -q "inet "; }

# Stop stale QMI state
/usr/bin/qmi-network "$QMI_DEV" stop 2>/dev/null || true
rm -f /tmp/qmi-network-state-cdc-wdm0 || true
sleep 1

# Retry until QMI modem is ready
for i in $(seq 1 12); do
    if /usr/bin/qmi-network "$QMI_DEV" start 2>/dev/null; then
        break
    fi
    logger -t qmi-autoconnect "Retrying QMI start ($i/12)"
    sleep 2
done

sleep 2

# Kill old DHCP client and start new one in background
pkill -f "udhcpc -i ${IFACE}" 2>/dev/null || true
/sbin/udhcpc -i "$IFACE" -b

# Set route metrics to prefer WiFi if available
if ! wlan_has_ipv4; then
    /sbin/ip route replace default dev "$IFACE" metric 600 || true
else
    /sbin/ip route replace default dev "$IFACE" metric 700 || true
fi

# Wait for IPv4 on wwan0
for i in $(seq 1 12); do
    if ip -4 addr show dev "$IFACE" | grep -q "inet "; then
        break
    fi
    sleep 1
done

# Write DNS safely
cat > "$DNS_FILE" <<DNS_EOF
nameserver $DNS1
nameserver $DNS2
DNS_EOF

logger -t qmi-autoconnect "QMI autoconnect completed"
exit 0
EOF
```

Set executable:

```bash
sudo chmod +x /usr/local/bin/qmi-autoconnect.sh
```

---

## 7. **Prevent NetworkManager Overwriting DNS**

```bash
sudo chattr +i /etc/resolv.conf
```

> This locks the file, ensuring NetworkManager does not replace your custom DNS.

---

## 8. **Create Systemd Service for Boot Autoconnect**

```bash
sudo tee /etc/systemd/system/qmi-autoconnect.service > /dev/null << 'EOF'
[Unit]
Description=Auto-start SIM7600G-H QMI network
After=network.target

[Service]
Type=oneshot
ExecStart=/usr/local/bin/qmi-autoconnect.sh
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF
```

Enable at boot:

```bash
sudo systemctl daemon-reload
sudo systemctl enable qmi-autoconnect.service
sudo systemctl start qmi-autoconnect.service
```

---

## 9. **Verify Network**

1. Check interface:

```bash
ip -4 addr show wwan0
```

2. Check routing:

```bash
ip route show
```

3. Test connectivity:

```bash
ping -I wwan0 8.8.8.8 -c3
ping google.com
```

* If `8.8.8.8` works but `google.com` fails → DNS misconfiguration.
* The script locks `/etc/resolv.conf` with 8.8.8.8 and 1.1.1.1 to ensure DNS works.

---

## 10. **Handling SIM or Dongle Changes**

* **New SIM / APN change:** Update `APN` in `/etc/qmi-network.conf`.
* **Dongle moved to new USB port:** Script auto-detects the first QMI device with `QMI_DEV=$(ls /dev/cdc-wdm* | head -n1)`.
* **Boot retries:** Script retries starting QMI 12 times, so slow modems are handled.

---

## 11. **Debugging Tips**

1. Check QMI status:

```bash
sudo qmicli -d /dev/cdc-wdm0 --nas-get-signal-info
sudo qmicli -d /dev/cdc-wdm0 --wds-get-packet-service-status
```

2. Check service logs:

```bash
sudo journalctl -xeu qmi-autoconnect.service
```

3. Remove DNS lock temporarily for troubleshooting:

```bash
sudo chattr -i /etc/resolv.conf
```

---

## 12. **Notes**

* The script ensures **robust boot-time internet**, even if the modem is slow.
* It avoids the **double EOF issue** when writing heredoc files.
* IP assignment and DHCP are handled via `udhcpc`.
* Routes are set dynamically, preferring WiFi if available.

---

✅ After completing these steps, the Raspberry Pi will automatically:

* Detect the SIM7600G-H modem
* Bring up QMI network
* Acquire an IP and default route
* Set DNS correctly
* Provide working internet at boot
