# Complete plug-and-play QMI setup for SIM7600G-H on Raspberry Pi OS (Raspberry Pi 5)

This is a single, self-contained reference anyone can use to make a SIM7600G-H USB dongle **plug-and-play** on Raspberry Pi OS (Debian), so that on a fresh boot the Pi:

* detects the USB modem (even if it’s plugged into a different port),
* switches it into **QMI** mode if needed,
* detects the SIM/operator (APN) and starts a data session,
* gets an IPv4 address via DHCP,
* configures routes so Wi-Fi is preferred and 4G is automatic failover,
* writes correct DNS and protects it from NetworkManager,
* retries / recovers if the modem is slow,
* logs everything for easy debugging.

Everything below is battle-tested with the steps and debugging we used during the session. Read once, then copy/paste the commands.

---

# Quick summary (one-line)

Create the script, install the systemd service, enable it — the script will do the rest. Full instructions below.

---

# Requirements

* Raspberry Pi 5 with Raspberry Pi OS (Debian) — arm architecture.
* `sudo` access.
* Packages: `libqmi-utils`, `usb-modeswitch`, `udhcpc` (script uses `/usr/sbin/qmi-network`, `/usr/bin/qmicli` and `/sbin/udhcpc`).

  ```bash
  sudo apt update
  sudo apt install libqmi-utils usb-modeswitch udhcpc -y
  ```
* A SIM7600G-H 4G dongle and a valid SIM card.

---

# What this package provides

1. `/usr/local/bin/qmi-autoconnect-plugplay.sh` — the automated script (with robust retries, selective APN detection, DNS handling and logging).
2. `/etc/systemd/system/qmi-autoconnect-plugplay.service` — systemd unit that runs the script at boot.
3. `/var/log/qmi-autoconnect.log` — debug log the script writes.

---

# Copy the script (safe single-EOF usage)

**Important:** when creating a script using `sudo tee` with an inner heredoc, use a *different* inner EOF marker to avoid the double-EOF problem we saw earlier. Copy and run exactly:

```bash
sudo tee /usr/local/bin/qmi-autoconnect-plugplay.sh > /dev/null <<'EOF'
#!/bin/bash
# qmi-autoconnect-plugplay.sh - Fully automated QMI modem setup for SIM7600G-H
set -euo pipefail

DEBUG_LOG="/var/log/qmi-autoconnect.log"
log() { echo "[$(date '+%F %T')] $*" | tee -a "$DEBUG_LOG"; }

DNS_FILE="/etc/resolv.conf"
DNS1="8.8.8.8"
DNS2="1.1.1.1"

# Helper: check if wlan0 has IPv4
wlan_has_ipv4() { ip -4 addr show dev wlan0 2>/dev/null | grep -q "inet "; }

# Detect first QMI device (cdc-wdm)
detect_qmi_device() {
  ls /dev/cdc-wdm* 2>/dev/null | head -n1 || true
}

# Try to switch modem to QMI via serial AT command (best-effort)
switch_to_qmi() {
  local tty
  tty=$(ls /dev/ttyUSB* 2>/dev/null | head -n1 || true)
  if [ -n "$tty" ]; then
    log "Attempting AT QCFG usbnet on $tty (best-effort)..."
    # best-effort write; silent if fails
    printf 'AT+QCFG="usbnet",1\r\n' > "$tty" 2>/dev/null || true
    sleep 2
    log "If device did not switch automatically, replug the dongle or wait a few seconds."
  else
    log "No serial ttyUSB found; skipping AT QCFG step."
  fi
}

# Simple APN detection using qmicli -> map MCC/MNC to APN (extendable)
detect_apn_from_sim() {
  local dev="$1"
  # get operator code: MCC MNC output lines contain MCC: 'xxx' MNC: 'yy'
  local op
  op=$(qmicli -d "$dev" --nas-get-home-network 2>/dev/null || true)
  # Extract MCC and MNC if available (fallback to 'internet')
  local mcc mnc
  mcc=$(printf '%s' "$op" | sed -n "s/.*MCC: '\([0-9]*\)'.*/\1/p" | head -n1 || true)
  mnc=$(printf '%s' "$op" | sed -n "s/.*MNC: '\([0-9]*\)'.*/\1/p" | head -n1 || true)
  if [ -z "$mcc" ]; then
    log "Could not detect MCC/MNC; using default APN 'internet'."
    printf 'internet'
    return
  fi
  log "Detected MCC=$mcc MNC=$mnc"
  # Very small example mapping — extend /etc/qmi-apn-mapping.conf for more carriers
  case "${mcc}${mnc}" in
    40490|40445|40481) printf 'airtelgprs.com' ;;  # Airtel examples
    40410) printf 'bsnl.apn' ;;                    # example
    44010) printf 'lte.kddi.ne.jp' ;;              # Japan (example)
    23415) printf 'ee.internet' ;;                 # UK (example)
    *) printf 'internet' ;;                        # fallback
  esac
}

start_qmi_network() {
  local dev="$1"
  # Try up to N attempts — modem can be slow
  local attempts=8
  local i
  for i in $(seq 1 $attempts); do
    log "qmi-network start attempt $i/$attempts on $dev"
    if /usr/bin/qmi-network "$dev" start 2>/dev/null; then
      log "qmi-network started."
      return 0
    fi
    sleep 2
  done
  log "qmi-network failed after $attempts attempts."
  return 1
}

wait_for_ip() {
  local iface="$1"
  for i in $(seq 1 12); do
    if ip -4 addr show dev "$iface" | grep -q "inet "; then
      log "$iface has IPv4."
      return 0
    fi
    sleep 2
  done
  log "Timeout waiting for IPv4 on $iface"
  return 1
}

start_dhcp() {
  local iface="$1"
  pkill -f "udhcpc -i ${iface}" 2>/dev/null || true
  /sbin/udhcpc -i "$iface" -b
}

set_route_metric() {
  local iface="$1"
  if ! wlan_has_ipv4; then
    /sbin/ip route replace default dev "$iface" metric 600 || true
  else
    /sbin/ip route replace default dev "$iface" metric 700 || true
  fi
}

configure_dns() {
  # allow writing resolv.conf, write it, then lock it to prevent NM overwriting
  chattr -i "$DNS_FILE" 2>/dev/null || true
  cat > "$DNS_FILE" <<'DNS_EOF'
nameserver __DNS1__
nameserver __DNS2__
DNS_EOF
  # replace placeholder tokens atomically so heredoc doesn't expand during tee; do it in-place
  sed -i "s/__DNS1__/${DNS1}/" "$DNS_FILE"
  sed -i "s/__DNS2__/${DNS2}/" "$DNS_FILE"
  chattr +i "$DNS_FILE" 2>/dev/null || true
  log "DNS written and locked: ${DNS1}, ${DNS2}"
}

# === main ===
log "=== qmi-autoconnect-plugplay starting ==="

# 1) Try to switch to QMI (best-effort)
switch_to_qmi

# 2) Detect QMI device
QMI_DEV="$(detect_qmi_device)"
if [ -z "$QMI_DEV" ]; then
  log "No /dev/cdc-wdm* device found. Give the modem 3 more seconds and retry."
  sleep 3
  QMI_DEV="$(detect_qmi_device)"
fi
if [ -z "$QMI_DEV" ]; then
  log "ERROR: No QMI device present. Aborting."
  exit 1
fi
log "Found QMI device: $QMI_DEV"

# 3) Detect APN
APN="$(detect_apn_from_sim "$QMI_DEV")"
log "APN chosen: $APN"
# Ensure qmi-network uses the APN — write quick temp conf if qmi-network reads /etc/qmi-network.conf
cat > /etc/qmi-network.conf <<QMIEOF
APN=$APN
IP_TYPE=4
qmi-proxy=yes
QMIEOF

# 4) Bring up QMI network
# Clear stale state
/usr/bin/qmi-network "$QMI_DEV" stop 2>/dev/null || true
rm -f /tmp/qmi-network-state-cdc-wdm0 2>/dev/null || true
sleep 1

if ! start_qmi_network "$QMI_DEV"; then
  log "ERROR: Could not start QMI network. See /var/log/qmi-autoconnect.log and journalctl -u qmi-autoconnect-plugplay.service"
  exit 2
fi

# 5) Start DHCP and wait for IP
IFACE="wwan0"
start_dhcp "$IFACE"
if ! wait_for_ip "$IFACE"; then
  log "ERROR: wwan0 did not obtain IPv4. Exiting."
  exit 3
fi

# 6) Routing and DNS
set_route_metric "$IFACE"
configure_dns

log "=== qmi-autoconnect-plugplay complete ==="
exit 0
EOF

sudo chmod +x /usr/local/bin/qmi-autoconnect-plugplay.sh
```

---

# Install the systemd service (single-EOF safe)

```bash
sudo tee /etc/systemd/system/qmi-autoconnect-plugplay.service > /dev/null <<'EOF'
[Unit]
Description=Auto QMI Modem Plug-and-Play (SIM7600G-H)
After=network.target

[Service]
Type=oneshot
ExecStart=/usr/local/bin/qmi-autoconnect-plugplay.sh
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable qmi-autoconnect-plugplay.service
sudo systemctl start qmi-autoconnect-plugplay.service
```

---

# How to use (step-by-step)

1. Run the package install prerequisites:

   ```bash
   sudo apt update
   sudo apt install libqmi-utils usb-modeswitch udhcpc -y
   ```

2. Copy the script (as above) and create the systemd service (as above).

3. Make sure ModemManager will not interfere (recommended). If ModemManager is present and grabs the device, create the ModemManager filter:

   ```bash
   sudo mkdir -p /etc/ModemManager/conf.d
   sudo tee /etc/ModemManager/conf.d/99-ignore-sim7600.conf > /dev/null <<'EOF'
   [filter]
   udev-property-match=ID_VENDOR_ID=1e0e
   udev-property-match=ID_MODEL_ID=9001
   EOF
   sudo systemctl restart ModemManager || true
   ```

4. Start service now:

   ```bash
   sudo systemctl start qmi-autoconnect-plugplay.service
   ```

5. Verify:

   ```bash
   ip -4 addr show wwan0
   ip route show
   cat /etc/resolv.conf
   ping -I wwan0 8.8.8.8 -c3
   ping -I wwan0 google.com -c3
   sudo journalctl -u qmi-autoconnect-plugplay.service -n 200 --no-pager
   sudo tail -n 200 /var/log/qmi-autoconnect.log
   ```

---

# Verification & expected outputs

* `ip -4 addr show wwan0` → shows `inet` address assigned (e.g. `100.x.x.x`).
* `ip route show` → should include a `default` via your wwan0 gateway OR wlan0 (wi-fi preferred) depending on availability.
* `cat /etc/resolv.conf` → should contain:

  ```
  nameserver 8.8.8.8
  nameserver 1.1.1.1
  ```

  (and the file will be `chattr +i` locked).
* `ping -I wwan0 8.8.8.8 -c3` → should reply.
* `ping google.com` → should reply (DNS resolution working).

---

# Troubleshooting (most common failures, with commands to run)

> If anything fails, run these to gather diagnostics and paste them when asking for help:

```bash
sudo journalctl -u qmi-autoconnect-plugplay.service --no-pager -n 200
sudo tail -n 200 /var/log/qmi-autoconnect.log
lsusb
dmesg | grep -i qmi
ip a
ip route
cat /etc/qmi-network.conf
sudo qmicli -d /dev/cdc-wdm0 --uim-get-card-status
sudo qmicli -d /dev/cdc-wdm0 --nas-get-serving-system
sudo qmicli -d /dev/cdc-wdm0 --wds-get-packet-service-status
```

### Common issues and fixes

* **No `/dev/cdc-wdm*` found**

  * Wait a few seconds after plugging in the modem. Replug. Check `dmesg`. If the device shows as `/dev/ttyUSB*`, the dongle may be in AT mode — the script attempts `AT+QCFG="usbnet",1` on the first `/dev/ttyUSB*`, but if that fails, replugging often shifts it into QMI.

* **`qmi-network` fails with `CallFailed` / `no-service`**

  * SIM not registered or APN wrong. Check `sudo qmicli -d /dev/cdc-wdm0 --nas-get-serving-system`. If no registration, check SIM contact, PIN, and operator. Confirm APN mapping: `/etc/qmi-network.conf` or extend `/etc/qmi-apn-mapping.conf` as described below.

* **DHCP fails / no IP assigned**

  * Run `sudo qmi-network /dev/cdc-wdm0 start` (manual) then `sudo udhcpc -i wwan0`. If DHCP still fails, try `journalctl -xe` to view `udhcpc` messages.

* **DNS keeps getting overwritten**

  * We lock `/etc/resolv.conf` with `chattr +i`. If you later need NetworkManager to manage DNS, undo with `sudo chattr -i /etc/resolv.conf`. Use this locking only if you want the script to manage DNS.

* **`Operation not permitted` while writing `/etc/resolv.conf`**

  * Remove immutable flag: `sudo chattr -i /etc/resolv.conf`, then re-run script.

* **Stale PDH / "PDH already exists"**

  * Stop network and remove state file:

    ```bash
    sudo qmi-network /dev/cdc-wdm0 stop || true
    sudo rm -f /tmp/qmi-network-state-cdc-wdm0
    sudo systemctl restart qmi-autoconnect-plugplay.service
    ```

---

# Advanced: APN mapping file (optional)

You can maintain a more complete APN map to improve operator detection. Create `/etc/qmi-apn-mapping.conf` with lines like:

```
MCCMNC=40490 APN=airtelgprs.com
MCCMNC=40410 APN=bsnl.apn
MCCMNC=23415 APN=ee.internet
```

Then change `detect_apn_from_sim()` in the script to look up `/etc/qmi-apn-mapping.conf` using the detected `MCC`+`MNC`. I kept the script simple but structured so you can extend it trivially.

---

# Safety & revert instructions (how to undo all automatic changes)

If you want to revert everything:

```bash
sudo systemctl stop qmi-autoconnect-plugplay.service
sudo systemctl disable qmi-autoconnect-plugplay.service
sudo rm -f /etc/systemd/system/qmi-autoconnect-plugplay.service
sudo rm -f /usr/local/bin/qmi-autoconnect-plugplay.sh
sudo rm -f /var/log/qmi-autoconnect.log
sudo rm -f /etc/qmi-network.conf
sudo chattr -i /etc/resolv.conf   # Allow NM to manage DNS again
```

(Then restart NetworkManager if needed.)

---

# Why we avoided the “double EOF” bug

When writing a file that itself contains a heredoc we used **different terminator tokens** so the outer `tee` heredoc and the inner `cat` heredoc never collide. The script writing commands above use `EOF` for the outer `tee` and `'DNS_EOF'` (or `EOF2` / `DNS_EOF`) inside the script to avoid accidental premature termination.

When you copy/paste the provided `sudo tee` blocks they are already safe.

---

# Appendices

## Useful manual commands (for experts)

* Show modem device:

  ```bash
  ls /dev/cdc-wdm* /dev/ttyUSB* 2>/dev/null || true
  ```
* QMI device info:

  ```bash
  sudo qmicli -d /dev/cdc-wdm0 --device-open-proxy --get-identifier
  ```
* Signal & registration:

  ```bash
  sudo qmicli -d /dev/cdc-wdm0 --nas-get-signal-strength
  sudo qmicli -d /dev/cdc-wdm0 --nas-get-serving-system
  ```
* WDS packet service status:

  ```bash
  sudo qmicli -d /dev/cdc-wdm0 --wds-get-packet-service-status
  ```

## Where logs are

* Script log: `/var/log/qmi-autoconnect.log`
* systemd journal: `sudo journalctl -u qmi-autoconnect-plugplay.service --no-pager`

---

# Final notes & recommendations

* The script is conservative: it uses public DNS (8.8.8.8/1.1.1.1) and locks `/etc/resolv.conf`. If you rely on local DNS (company, captive portal), remove the `chattr +i` line.
* If you want **complete global cellular APN coverage**, I can add a full MCC/MNC→APN database (small file) and code to consult it. Say “Yes — add APN database” and I’ll provide the mapping file and the updated script.
* Keep the `libqmi-utils` package installed — it provides `qmicli` and `qmi-network` which are central to this flow.

---
