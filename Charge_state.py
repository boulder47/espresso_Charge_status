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

GET_BATTERY_INFO = bytes([0xf3, 0x05, 0x10, 0x00])

with serial.Serial('/dev/ttyUSB0', baudrate=115200, timeout=2) as ser:
    cmd = GET_BATTERY_INFO
    payload = cmd + bytes([xor_checksum(cmd)])
    encoded = cobs_encode(payload) + b'\x00'
    ser.write(encoded)
    time.sleep(0.5)
    raw = ser.read_until(b'\x00', size=256)

packet = raw[:-1]
decoded = cobs_decode(packet)

data_checksum = decoded[-1]
calc = xor_checksum(decoded[:-1])
assert data_checksum == calc, f"Checksum mismatch: got {data_checksum:#04x}, expected {calc:#04x}"

soc         = decoded[0]
soh         = decoded[1]
remaining   = struct.unpack('<H', decoded[2:4])[0]   # little-endian
full_cap    = struct.unpack('<H', decoded[4:6])[0]   # little-endian
voltage     = struct.unpack('>H', bytes(reversed(decoded[6:8])))[0]
current     = struct.unpack('>H', bytes(reversed(decoded[8:10])))[0]
temp_raw    = struct.unpack('>H', bytes(reversed(decoded[10:12])))[0]
temperature = round(temp_raw * 0.1 - 273.15, 2)
time_empty  = struct.unpack('>H', bytes(reversed(decoded[12:14])))[0]
time_full   = struct.unpack('>H', bytes(reversed(decoded[14:16])))[0]
power_dir   = decoded[16]

print(f"SOC: {soc}%  SOH: {soh}%")
print(f"Voltage: {voltage / 1000:.3f} V  Current: {current} mA")
print(f"Temp: {temperature} °C")
print(f"Remaining: {remaining} mAh / {full_cap} mAh")
print(f"Time to empty: {time_empty if time_empty != 0xFFFF else 'N/A'} min")
print(f"Time to full:  {time_full  if time_full  != 0xFFFF else 'N/A'} min")
print(f"Power direction: {'SINK (charging)' if power_dir == 0 else 'SOURCE (discharging)'}")
