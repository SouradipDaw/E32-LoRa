"""
E32-900T30D Receiver  —  Module B
UART : /dev/ttyAMA4  (GPIO 12 TX / GPIO 13 RX)  — dtoverlay=uart5
AUX  : GPIO 24  (Pin 18)
M0   : GPIO 23  (Pin 16)
M1   : GPIO 25  (Pin 22)

Note: dtoverlay=uart5 maps to /dev/ttyAMA4 on Pi 4B, NOT ttyAMA5.
"""

import serial
import lgpio
import time

# ── Pin config ───────────────────────────────────────────
M0_PIN  = 23
M1_PIN  = 24
AUX_PIN = 25

UART_PORT = "/dev/ttyAMA4"
BAUD      = 9600

# ── GPIO setup ───────────────────────────────────────────
h = lgpio.gpiochip_open(0)
lgpio.gpio_claim_output(h, M0_PIN)
lgpio.gpio_claim_output(h, M1_PIN)
lgpio.gpio_claim_input(h, AUX_PIN)

def set_mode_normal():
    lgpio.gpio_write(h, M0_PIN, 0)
    lgpio.gpio_write(h, M1_PIN, 0)
    time.sleep(0.1)

def wait_aux_high(timeout=3.0):
    start = time.time()
    while time.time() - start < timeout:
        if lgpio.gpio_read(h, AUX_PIN) == 1:
            return True
        time.sleep(0.01)
    print("[WARN] AUX timeout")
    return False

# ── Serial setup ─────────────────────────────────────────
ser = serial.Serial(
    port=UART_PORT,
    baudrate=BAUD,
    bytesize=serial.EIGHTBITS,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    timeout=1
)

# ── Main ─────────────────────────────────────────────────
def main():
    set_mode_normal()
    wait_aux_high()
    print(f"[RX] Listening on {UART_PORT} ...")

    buffer = b""
    try:
        while True:
            if ser.in_waiting > 0:
                buffer += ser.read(ser.in_waiting)
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    message = line.decode("utf-8", errors="replace").strip()
                    if message:
                        print(f"[RX] Received: {message}")
            time.sleep(0.05)

    except KeyboardInterrupt:
        print("\n[RX] Stopped.")
    finally:
        ser.close()
        lgpio.gpiochip_close(h)

if __name__ == "__main__":
    main()
