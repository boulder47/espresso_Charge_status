import serial
import struct
import time

def cobs_decode(data):
    out = []
    i = 0
    while i < len(data):
        code = data[i]
        i += 1
        for _ in range(1, code):
            if i >= len(data):
                break
            out.append(data[i])
            i += 1
        if code < 0xFF and i < len(data):
            out.append(0x00)
    return bytes(out)

def cobs_encode(data):
    out = []
    data = list(data) + [0x00]
    code_idx = 0
    out.append(0x00)
    code = 1
    for byte in data:
        if byte == 0x00:
            out[code_idx] = code
            code_idx = len(out)
            out.append(0x00)
            code = 1
        else:
            out.append(byte)
            code += 1
            if code == 0xFF:
                out[code_idx] = code
                code_idx = len(out)
                out.append(0x00)
                code = 1
    return bytes(out[:-1])

def xor_checksum(data):
    result = 0
    for b in data:
        result ^= b
    return result

def to_signed16(value):
    """Reinterpret an unsigned 16-bit value as signed (two's complement)."""
    return value - 0x10000 if value >= 0x8000 else value

GET_BATTERY_INFO = bytes([0xf3, 0x05, 0x10, 0x00])

with serial.Serial('/dev/ttyUSB0', baudrate=115200, timeout=2) as ser:
    cmd = GET_BATTERY_INFO
    payload = cmd + bytes([xor_checksum(cmd)])
    encoded = cobs_encode(payload) + b'\x00'
    ser.write(encoded)
    time.sleep(0.5)
    raw = ser.read_until(b'\x00', size=256)

if not raw or raw[-1] != 0x00:
    print(f"Incomplete or empty response ({len(raw)} bytes): {raw.hex()}")
    exit(1)

packet = raw[:-1]
decoded = cobs_decode(packet)

if len(decoded) < 18:
    print(f"Response too short after decode ({len(decoded)} bytes): {decoded.hex()}")
    exit(1)

data_checksum = decoded[-1]
calc = xor_checksum(decoded[:-1])
if data_checksum != calc:
    print(f"Checksum mismatch: got {data_checksum:#04x}, expected {calc:#04x}")
    exit(1)

soc           = decoded[0]
soh           = decoded[1]
# NOTE: charge.js reads these big-endian (readUInt16BE with no swap), but that produces
# physically impossible values (full capacity swinging from ~63800 to ~3300 between reads
# of the same battery, and remaining > full at 100% SOC in one case). Little-endian gives
# stable, sane values across repeated reads (full capacity ~5113-5133 consistently), so we
# use little-endian here -- this appears to be a bug in the original charge.js.
remaining     = struct.unpack('<H', decoded[2:4])[0]
full_cap      = struct.unpack('<H', decoded[4:6])[0]
voltage       = struct.unpack('>H', bytes(reversed(decoded[6:8])))[0]
current_raw   = struct.unpack('>H', bytes(reversed(decoded[8:10])))[0]
current       = to_signed16(current_raw)               # signed: negative = discharging
temp_raw      = struct.unpack('>H', bytes(reversed(decoded[10:12])))[0]
temperature   = round(temp_raw * 0.1 - 273.15, 2)
time_empty    = struct.unpack('>H', bytes(reversed(decoded[12:14])))[0]
time_full     = struct.unpack('>H', bytes(reversed(decoded[14:16])))[0]
power_dir     = decoded[16]

print(f"SOC: {soc}%  SOH: {soh}%")
print(f"Voltage: {voltage / 1000:.3f} V  Current: {current} mA")
print(f"Temp: {temperature} °C")
print(f"Remaining: {remaining} mAh / {full_cap} mAh")

remaining_wh = round(remaining * (voltage / 1000) / 1000, 2)
full_wh = round(full_cap * (voltage / 1000) / 1000, 2)
print(f"Remaining: {remaining_wh} Wh / {full_wh} Wh (at live pack voltage)")

# Time to empty: not meaningful while charging or at full charge
if power_dir == 0 or soc == 100 or time_empty == 0xFFFF:
    print("Time to empty: N/A")
else:
    print(f"Time to empty: {time_empty} min")

# Time to full: not meaningful while discharging or already at full charge
if power_dir != 0 or time_full == 0xFFFF:
    print("Time to full:  N/A")
elif soc == 100 and time_full == 0:
    print("Time to full:  Done")
else:
    print(f"Time to full:  {time_full} min")

print(f"Power direction: {'SINK (charging)' if power_dir == 0 else 'SOURCE (discharging)'}")
