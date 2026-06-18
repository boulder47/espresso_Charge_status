# espresso_Charge_status
Python script for getting the state of Espresso Charge power bank


Device:
https://us.espres.so/products/espresso-charge

# Charge Battery Reader

A Python script to read battery telemetry from a **Charge** battery device over USB serial on Linux.

The device uses a Silicon Labs CP210x USB-to-UART bridge and communicates via a COBS-encoded binary protocol.

---

## Prerequisites

### Hardware
- Charge battery device connected via USB

### OS / Kernel
- Linux with the `cp210x` kernel module (included in most distributions by default)
- Verify it is loaded:
  ```bash
  lsmod | grep cp210x
  ```
- If missing, load it manually:
  ```bash
  sudo modprobe cp210x
  ```

### Serial port permissions
By default, `/dev/ttyUSB*` devices require root or membership in the `dialout` group.

Add your user to the group (recommended):
```bash
sudo usermod -aG dialout $USER
```
Then **log out and back in** for the change to take effect.

Or for a one-off temporary fix:
```bash
sudo chmod 666 /dev/ttyUSB0
```

### Python
- Python 3.7 or later
- `pyserial` library:
  ```bash
  pip install pyserial --break-system-packages
  ```
  Or inside a virtual environment:
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  pip install pyserial
  ```

---

## Finding the device port

After plugging in the device, confirm it is detected:
```bash
lsusb | grep "10c4"
# Silicon Laboratories CP210x USB to UART Bridge

ls /dev/ttyUSB*
# e.g. /dev/ttyUSB0
```

For a stable path that survives reboots:
```bash
ls /dev/serial/by-id/
# e.g. usb-Silicon_Labs_CP2102_...-port0
```

---

## Usage

```bash
python3 readcharge.py
```

By default the script connects to `/dev/ttyUSB0`. If your device appears on a different port, edit this line near the top of the script:

```python
with serial.Serial('/dev/ttyUSB0', baudrate=115200, timeout=2) as ser:
```

### Example output

```
SOC: 97%  SOH: 83%
Voltage: 20.715 V  Current: 58 mA
Temp: 35.95 °C
Remaining: 4928 mAh / 5113 mAh
Time to empty: N/A min
Time to full:  Done
Power direction: SINK (charging)
```

### Field reference

| Field | Description |
|---|---|
| SOC | State of Charge — current charge level (%) |
| SOH | State of Health — battery condition vs new (%) |
| Voltage | Pack voltage in volts |
| Current | Charge/discharge current in mA |
| Temp | Battery temperature in °C |
| Remaining | Current usable capacity in mAh |
| Full capacity | Maximum capacity at current SOH in mAh |
| Time to empty | Estimated minutes of runtime remaining (`N/A` when charging) |
| Time to full | Estimated minutes until fully charged (`Done` when at 100%) |
| Power direction | `SINK` = charging, `SOURCE` = discharging |

---

## Protocol notes

| Parameter | Value |
|---|---|
| USB Vendor ID | `10c4` (Silicon Laboratories) |
| USB Product ID | `ea60` (CP210x) |
| Baud rate | 115200 |
| Framing | COBS-encoded, `0x00`-terminated packets |
| Checksum | XOR of all payload bytes, appended before encoding |
| Capacity fields | 16-bit little-endian |
| Voltage / current / temp / time fields | 16-bit, byte-swapped then big-endian |
| Temperature conversion | `raw × 0.1 − 273.15` (Kelvin → °C) |
