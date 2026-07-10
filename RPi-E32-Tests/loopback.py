"""
Raspberry Pi Loopback Test
---------------------------

Usage:
  python3 loopback.py --port /dev/ttyAMA* ; insert UART port number in place of *

Default port /dev/ttyAMA0

Short TXD and RXD pins of respective UART port of Raspberry Pi
"""


import serial, time
import argparse

ap = argparse.ArgumentParser(description= "RPi Loopback Port")
ap.add_argument("--port", default = "/dev/ttyAMA0")
args = ap.parse_args()

ser = serial.Serial(args.port, baudrate=9600, timeout=1, write_timeout = 1)
ser.reset_input_buffer()

test = bytes([0xAA, 0xBB, 0xCC])
ser.write(test)
time.sleep(0.1)
resp = ser.read(len(test))
print(f"Sent:     {test.hex()}")
print(f"Received: {resp.hex()}")
print("UART OK" if resp == test else "UART FAIL — no loopback")

ser.close()
