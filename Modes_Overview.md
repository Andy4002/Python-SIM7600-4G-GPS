**Overview** of all SIM7600G-H USB/network modes, what they do, their pros/cons, and **how to switch them on 4G dongle** specifically.

---

# ✅ 1. The Three Families of Modem Modes

| Mode                  | Underlying Technology        | Kernel Interface          | Performance                    | Use Case                                  |
| --------------------- | ---------------------------- | ------------------------- | ------------------------------ | ----------------------------------------- |
| **PPP**               | Old serial dial-up emulation | /dev/ttyUSBx              | ❌ Slow (3–8 Mbps)              | Legacy microcontrollers, very old routers |
| **RNDIS / ECM / NCM** | USB Ethernet emulation       | `usb0` / `eth1` style     | ✅ Medium (20–60 Mbps)          | Plug-and-play internet, easiest to use    |
| **QMI / MBIM**        | Native modem control         | `wwan0` + `/dev/cdc-wdm0` | ✅✅ Fastest (50–110 Mbps on Pi) | Linux routers, RPi5, performance critical |

---

# ✅ 2. What they mean conceptually

### 🔹 PPP (Point-to-Point Protocol)

* Talks over **AT commands** only
* Connect like a dial-up modem (`ATD*99***1#`)
* Very old but universal
* No good for modern speeds

### 🔹 RNDIS / ECM / NCM (USB Ethernet)

* Modem pretends to be a **USB network card**
* The modem does the NAT itself (like a phone hotspot over USB)
* PC/RPi just sees an **ethernet device**
* Easy to bring up, no qmi tools needed

**RNDIS** = Windows style
**ECM** = Linux style
**NCM** = Faster ECM

### 🔹 QMI / MBIM (Advanced Modem Control)

* Linux controls the radio and IP stack directly
* Uses `/dev/cdc-wdm0` for control messages
* Gives full statistics and power control
* QMI = Qualcomm proprietary (best for 7600)
* MBIM = Microsoft standard (works too)

---

# ✅ 3. Which one does your SIM7600 currently use?

From your output earlier:

```
AT+CSUB=0
```

This = **RNDIS/NCM mode** (composition 0)

You are **not** in QMI yet.

---

# ✅ 4. How to switch on SIM7600G-H

| Target Mode  | Command                        | Notes                     |
| ------------ | ------------------------------ | ------------------------- |
| ✅ QMI (best) | `AT+CSUB=1` then `AT+CFUN=1,1` | Requires qmi_wwan driver  |
| ✅ MBIM       | `AT+CSUB=2` then `AT+CFUN=1,1` | Works with `mbim-network` |
| ✅ RNDIS/NCM  | `AT+CSUB=0` then `AT+CFUN=1,1` | Plug-and-play             |
| ❌ PPP        | Disable USB, use /dev/ttyUSB3  | Obsolete on Pi            |

> ✅ Only `CSUB` works on your firmware.
> ❌ `CSUSB` is not available on LE20B04 builds.

---

# ✅ 5. Commands to set each mode (4G dongle MODEL)

### 🔸 Switch to QMI mode (recommended)

```
AT+CSUB=1
AT+CFUN=1,1
```

### 🔸 Switch to MBIM mode

```
AT+CSUB=2
AT+CFUN=1,1
```

### 🔸 Switch back to RNDIS/ECM/NCM (current)

```
AT+CSUB=0
AT+CFUN=1,1
```

(Each requires reboot of modem using `+CFUN=1,1`)

---

# ✅ 6. Which mode should YOU use for RPi5 + 4G?

| Category                     | Best Choice |
| ---------------------------- | ----------- |
| Remote desktop (low latency) | ✅ QMI       |
| Power saving / consistent    | ✅ QMI       |
| Speed                        | ✅ QMI       |
| Easiest setup                | RNDIS/NCM   |
| Windows compatibility        | MBIM        |
| DO NOT USE                   | PPP         |

Since you want **remote desktop + stable uplink**, **QMI is the correct mode**.

---

Before I move you to the final part (autoconnect service, watchdog, and faster radio tuning), confirm:

### ✅ "yes switch to QMI"

if you want me to guide you through switching cleanly

or

### ✅ "keep RNDIS"

if you prefer plug-and-play mode


---

## Note: For changing modes or monitoring modems, use commands: 

'''
sudo screen /dev/ttyUSB2 115200
'''

OR

'''
sudo minicom -D /dev/ttyUSB2
'''
