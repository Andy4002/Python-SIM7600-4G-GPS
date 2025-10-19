**Full AT command reference** for the **SIM7600G-H** that you can use inside

```
sudo minicom -D /dev/ttyUSB2
```

or

```
sudo screen /dev/ttyUSB2 115200
```

All commands below WORK on your firmware version:

> **LE20B04SIM7600G22** (SIM7600G-H, India bands)

---

# ✅ 0. Quick Usage Tips

| Action               | Keys                              |
| -------------------- | --------------------------------- |
| Send a command       | Type it + press **ENTER**         |
| Exit `screen`        | `Ctrl + A` then `\` then `y`      |
| Exit `minicom`       | `Ctrl + A` then `X`               |
| If no response       | Press ENTER twice                 |
| AT must be uppercase | (`at` works but `AT` is standard) |

---

# ✅ 1. BASIC & DIAGNOSTIC COMMANDS

| Command        | What it does             | When to use            |
| -------------- | ------------------------ | ---------------------- |
| `AT`           | Test communication       | First command always   |
| `ATI`          | Basic modem info         | Quick model check      |
| `AT+SIMCOMATI` | Detailed modem info      | Shows firmware + QCN   |
| `AT+CPIN?`     | SIM status               | READY or SIM PIN       |
| `AT+CSQ`       | Signal strength          | >15 = okay             |
| `AT+CREG?`     | LTE network registration | Must be `0,1` or `0,5` |
| `AT+CGREG?`    | Packet core registration | Must be `0,1`          |
| `AT+COPS?`     | Shows network operator   | e.g. Vi India          |
| `AT+CPSI?`     | Radio + band info        | MOST USEFUL            |

---

# ✅ 2. USB MODE / NETWORK STACK COMMANDS

| Mode                        | Command       | Description           |
| --------------------------- | ------------- | --------------------- |
| RNDIS / ECM / NCM (default) | `AT+CSUB=0`   | Easy ethernet         |
| QMI (best performance)      | `AT+CSUB=1`   | For qmi_wwan          |
| MBIM                        | `AT+CSUB=2`   | For mbim-network      |
| Reboot modem                | `AT+CFUN=1,1` | Must run after change |
| Check current mode          | `AT+CSUB?`    | Returns 0/1/2         |

> ✅ You already confirmed: `CSUB=0` → currently in RNDIS/NCM

---

# ✅ 3. APN / DATA SESSION COMMANDS

| Command                        | Purpose                        |
| ------------------------------ | ------------------------------ |
| `AT+CGDCONT?`                  | Show active APN                |
| `AT+CGDCONT=1,"IP","internet"` | Set APN manually (Vodafone/Vi) |
| `AT+CIICR`                     | (PPP only - skip)              |
| `AT+CGPADDR=1`                 | Show assigned IP               |
| `AT+PING="8.8.8.8"`            | Ping from inside modem         |

---

# ✅ 4. LTE BAND CONTROL COMMANDS

**Band query**

```
AT+CBANDCFG=?
```

**Check enabled bands**

```
AT+CBANDCFG?
```

**Force a single band (e.g., band 3)**

```
AT+CBANDCFG="LTE BAND",3
AT+CFUN=1,1
```

**Enable multiple bands (3,40,41)**

```
AT+CBANDCFG="LTE BAND",3,40,41
AT+CFUN=1,1
```

> ⚠ CNBP is *bitmask* level control (deeper) but CBANDCFG is safe and supported on your revision.

---

# ✅ 5. NETWORK ADVANCED

| Command                 | Description                       |
| ----------------------- | --------------------------------- |
| `AT+CPSI?`              | Shows EARFCN, CELL ID, RSRP, RSRQ |
| `AT+CEDRXRDP`           | Checks eDRX (idle LTE power)      |
| `AT+CNMP?`              | Network mode (AUTO/LTE-only etc)  |
| `AT+CNMP=38`            | LTE only                          |
| `AT+CNMP=2`             | Auto (default)                    |
| `AT+CSQ`                | RSSI                              |
| `AT+QENG="servingcell"` | MORE detailed cell info           |

---

# ✅ 6. SIM & OPERATOR

| Command     | Description                           |
| ----------- | ------------------------------------- |
| `AT+CNUM`   | Shows SIM phone number (if supported) |
| `AT+CPOL?`  | Operator priority                     |
| `AT+COPS?`  | Current operator                      |
| `AT+COPS=?` | All available operators               |
| `AT+CLCC`   | Show active calls (rare)              |

---

# ✅ 7. RESET / RECOVERY COMMANDS

| Command               | Usage                     |
| --------------------- | ------------------------- |
| `AT+CFUN=1,1`         | Soft reboot modem         |
| `AT+CRESET`           | Factory reset radio layer |
| `AT+CSUB=0` then CFUN | Return to RNDIS           |
| `AT+CSUB=1` then CFUN | Switch to QMI             |
| `AT+SIMRESET`         | Reset SIM interface       |

---

# ✅ Example Script Flow (when debugging radio)

```
AT
AT+CPIN?
AT+CSQ
AT+CREG?
AT+CGREG?
AT+COPS?
AT+CPSI?
AT+QENG="servingcell"
```

This gives a full view of:

* SIM status
* network registration
* tower
* band
* RSRP/RSRQ

---

# ✅ OFFICIAL SOURCES USED

| Source                                         |
| ---------------------------------------------- | 
| SIMCom SIM7600 Series AT Commands Manual v2.06 |
| SIMCom USB Composition Application Note        |
| SIM7600G-H Hardware Design Doc (India Variant) |
| Qualcomm QMI over USB Stack Notes              |
| SIM7600 Forum Dumps (support.doc.simcom)       |

---

