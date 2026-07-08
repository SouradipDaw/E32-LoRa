"""
E32-900T30D Transmitter  —  Module A
UART : /dev/ttyAMA0  (GPIO 14 TX / GPIO 15 RX)
AUX  : GPIO 22  (Pin 15)
M0   : GPIO 17  (Pin 11)
M1   : GPIO 27  (Pin 13)
"""

import serial
import lgpio
import time

# ── Pin config ───────────────────────────────────────────
M0_PIN  = 17
M1_PIN  = 27
AUX_PIN = 22

UART_PORT = "/dev/ttyAMA2"
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
    print(f"[TX] Ready on {UART_PORT}")

    count = 0
    try:
        while True:
            message = 45
            #f"Hello from TX | count={count}"
            payload = (message + "\n").encode("utf-8")
            wait_aux_high()
            ser.write(payload)
            print(f"[TX] Sent: {message}")
            count += 1
            time.sleep(2)

    except KeyboardInterrupt:
        print("\n[TX] Stopped.")
    finally:
        ser.close()
        lgpio.gpiochip_close(h)

if __name__ == "__main__":
    main()
