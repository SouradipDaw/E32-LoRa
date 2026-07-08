import serial, time

ser = serial.Serial("/dev/ttyAMA3", baudrate=9600, timeout=1)
ser.reset_input_buffer()

test = bytes([0xAA, 0xBB, 0xCC])
ser.write(test)
time.sleep(0.1)
resp = ser.read(3)
print(f"Sent:     {test.hex()}")
print(f"Received: {resp.hex()}")
print("UART OK" if resp == test else "UART FAIL — no loopback")

ser.close()
