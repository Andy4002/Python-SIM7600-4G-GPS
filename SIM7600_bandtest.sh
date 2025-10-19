#!/bin/bash
# SIM7600 Band Testing Script (v2 - Safe + Smart)

LOGFILE="/var/log/sim7600_bandtest.log"
DEVICE="/dev/ttyUSB2"
BANDS=(8 5 3 40 41)

echo "=== SIM7600 Band Test started $(date) ===" | tee -a "$LOGFILE"

for BAND in "${BANDS[@]}"; do
    echo -e "\n--- Testing LTE Band $BAND ---" | tee -a "$LOGFILE"

    echo "AT+CNMP=38" > "$DEVICE"        # LTE only
    sleep 1
    echo "AT+CBANDCFG=\"LTE BAND\",$BAND" > "$DEVICE"
    sleep 1
    echo "AT+CFUN=1,1" > "$DEVICE"
    sleep 15

    # Wait for registration
    echo "Checking network..." | tee -a "$LOGFILE"
    for i in {1..15}; do
        echo "AT+CREG?" > "$DEVICE"
        grep -q "+CREG: 0,1" <(timeout 1 cat "$DEVICE") && break
        sleep 2
    done

    echo "AT+CPSI?" > "$DEVICE"
    timeout 2 cat "$DEVICE" | tee -a "$LOGFILE"

    echo "AT+CSQ" > "$DEVICE"
    timeout 2 cat "$DEVICE" | tee -a "$LOGFILE"

    # Try to get IP
    echo "Activating PDP..." | tee -a "$LOGFILE"
    echo "AT+CGACT=1,1" > "$DEVICE"
    sleep 2
    echo "AT+CGPADDR=1" > "$DEVICE"
    timeout 2 cat "$DEVICE" | tee -a "$LOGFILE"

    # Try ping via modem AT
    echo "AT+PING=\"8.8.8.8\"" > "$DEVICE"
    timeout 10 cat "$DEVICE" | tee -a "$LOGFILE"

    echo "--- Band $BAND test complete ---" | tee -a "$LOGFILE"
done

echo "=== Band Test Complete $(date) ===" | tee -a "$LOGFILE"

