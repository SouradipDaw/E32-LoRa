"""
E32-900T30D LoRa Module Configurator for Raspberry Pi
======================================================
Uses: lgpio (preferred on Pi OS Bookworm+) + pyserial
Install: pip install lgpio pyserial

Wiring:
  E32 VCC  -> External 3.3V (NOT Pi's onboard pin — module draws ~1A on TX)
  E32 GND  -> GND
  E32 RXD  -> GPIO14 (Pi TXD, /dev/serial0)
  E32 TXD  -> GPIO15 (Pi RXD, /dev/serial0)
  E32 M0   -> GPIO17
  E32 M1   -> GPIO27
  E32 AUX  -> GPIO22

Enable hardware UART first:
  sudo raspi-config -> Interface Options -> Serial Port
    Login shell over serial? -> No
    Serial hardware enabled? -> Yes
  Then reboot.
"""

import lgpio
import serial
import time

# ── Pin definitions (BCM) ─────────────────────────────────────────────────────
M0_PIN  = 17
M1_PIN  = 27
AUX_PIN = 22

SERIAL_PORT = "/dev/ttyAMA2"
BAUD_RATE   = 9600


# ── GPIO helpers ──────────────────────────────────────────────────────────────

def gpio_setup(h):
    lgpio.gpio_claim_output(h, M0_PIN)
    lgpio.gpio_claim_output(h, M1_PIN)
    lgpio.gpio_claim_input(h, AUX_PIN)


def set_mode(h, m0, m1, timeout=3.0):
    """Set M0/M1 and wait for AUX HIGH (module ready)."""
    wait_aux_high(h, timeout)
    lgpio.gpio_write(h, M0_PIN, m0)
    lgpio.gpio_write(h, M1_PIN, m1)
    time.sleep(0.1)          # module needs ~1 ms; 100 ms is safe
    wait_aux_high(h, timeout)


def wait_aux_high(h, timeout=3.0):
    deadline = time.time() + timeout
    while lgpio.gpio_read(h, AUX_PIN) == 0:
        if time.time() > deadline:
            raise TimeoutError("AUX pin did not go HIGH — check wiring/power")
        time.sleep(0.01)


# ── Config protocol ───────────────────────────────────────────────────────────

def read_config(ser):
    """Send 0xC1 0xC1 0xC1, return 6-byte response."""
    ser.reset_input_buffer()
    ser.write(bytes([0xC1, 0xC1, 0xC1]))
    time.sleep(0.1)
    resp = ser.read(6)
    if len(resp) < 6:
        raise RuntimeError(f"Read config: got {len(resp)} bytes, expected 6")
    if resp[0] not in (0xC0, 0xC1):
        raise RuntimeError(f"Unexpected response header: 0x{resp[0]:02X}")
    return resp


def write_config(ser, addh, addl, sped, chan, option, save=True):
    """
    Write registers.
      save=True  -> 0xC0: persists to flash
      save=False -> 0xC2: temporary (lost on power-off)
    Module echoes the packet back on success.
    """
    cmd = 0xC0 if save else 0xC2
    ser.reset_input_buffer()
    ser.write(bytes([cmd, addh, addl, sped, chan, option]))
    time.sleep(0.2)
    echo = ser.read(6)
    if len(echo) < 6:
        raise RuntimeError(f"Write config: no echo received ({len(echo)} bytes)")
    return echo


# ── Register byte builders ────────────────────────────────────────────────────
#
# SPED byte:
#   bits [7:6] parity    00=8N1  01=8O1  10=8E1  11=8N1
#   bits [5:3] UART baud 001=1200 010=2400 011=4800 100=9600
#                        101=19200 110=38400 111=115200
#   bits [2:0] air rate  001=300 010=1200 011=2400 100=4800
#                        101=9600 110=19200
#
# OPTION byte:
#   bit  7    TX mode  0=transparent  1=fixed
#   bit  6    pull-up  0=open-collector  1=enabled
#   bits[5:3] WOR wakeup time (ms): 000=250 … 111=2000
#   bit  2    FEC  0=off  1=on
#   bits[1:0] TX power  00=30dBm 01=27dBm 10=24dBm 11=21dBm

_UART_BAUD = {1200:0b001, 2400:0b010, 4800:0b011, 9600:0b100,
              19200:0b101, 38400:0b110, 115200:0b111}
_AIR_RATE  = {300:0b001, 1200:0b010, 2400:0b011, 4800:0b100,
              9600:0b101, 19200:0b110}
_PARITY    = {"8N1":0b00, "8O1":0b01, "8E1":0b10}
_TX_POWER  = {30:0b00, 27:0b01, 24:0b10, 21:0b11}
_WAKE_TIME = {250:0b000, 500:0b001, 750:0b010, 1000:0b011,
              1250:0b100, 1500:0b101, 1750:0b110, 2000:0b111}

def make_sped(uart_baud=9600, air_rate=2400, parity="8N1"):
    return (_PARITY[parity] << 6) | (_UART_BAUD[uart_baud] << 3) | _AIR_RATE[air_rate]

def make_option(fixed_mode=False, pull_up=True, wakeup_ms=250,
                fec=True, tx_power_dbm=30):
    return ((1 if fixed_mode else 0) << 7 |
            (1 if pull_up   else 0) << 6 |
            _WAKE_TIME[wakeup_ms]   << 3 |
            (1 if fec       else 0) << 2 |
            _TX_POWER[tx_power_dbm])


# ── Human-readable decode ─────────────────────────────────────────────────────

def decode_config(raw):
    _, addh, addl, sped, chan, option = raw
    ub  = (sped >> 3) & 0b111
    ar  = sped & 0b111
    par = (sped >> 6) & 0b11
    wt  = (option >> 3) & 0b111

    inv_uart = {v: k for k, v in _UART_BAUD.items()}
    inv_air  = {v: k for k, v in _AIR_RATE.items()}
    inv_par  = {v: k for k, v in _PARITY.items()}
    inv_pwr  = {v: k for k, v in _TX_POWER.items()}
    inv_wake = {v: k for k, v in _WAKE_TIME.items()}

    freq_mhz = 862 + chan   # 900T30D: ch0 = 862 MHz, 1 MHz steps

    print("─" * 42)
    print(f"  Address      : 0x{addh:02X}{addl:02X}  ({addh * 256 + addl})")
    print(f"  UART baud    : {inv_uart.get(ub, '?')} bps")
    print(f"  Parity       : {inv_par.get(par, '?')}")
    print(f"  Air data rate: {inv_air.get(ar, '?')} bps")
    print(f"  Channel      : {chan}  ({freq_mhz} MHz)")
    print(f"  TX mode      : {'Fixed' if option & 0x80 else 'Transparent'}")
    print(f"  Pull-up      : {'Enabled' if option & 0x40 else 'Disabled'}")
    print(f"  Wakeup time  : {inv_wake.get(wt, '?')} ms")
    print(f"  FEC          : {'On' if option & 0x04 else 'Off'}")
    print(f"  TX power     : {inv_pwr.get(option & 0b11, '?')} dBm")
    print("─" * 42)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    # ── Edit these to match your desired config ──────────────────────────────
    NEW_ADDRESS   = 0x0000   # must match on both modules
    NEW_CHANNEL   = 0x06     # ch6 = 868 MHz; use 0x12 (18) for 900 MHz
    NEW_UART_BAUD = 9600
    NEW_AIR_RATE  = 2400     # bps — lower = longer range
    NEW_TX_POWER  = 30       # dBm (30 = max for 900T30D)
    FIXED_MODE    = False    # False = transparent, True = addressed/fixed
    FEC_ON        = True
    # ─────────────────────────────────────────────────────────────────────────

    h = lgpio.gpiochip_open(0)
    gpio_setup(h)

    try:
        with serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1.0) as ser:

            # 1. Enter sleep/config mode (M0=1, M1=1)
            print("[1] Entering sleep/config mode...")
            set_mode(h, m0=1, m1=1)
            print("    Module ready.\n")

            # 2. Read current config
            print("[2] Reading current configuration...")
            raw = read_config(ser)
            print(f"    Raw  : {' '.join(f'0x{b:02X}' for b in raw)}")
            decode_config(raw)

            # 3. Build and write new config
            addh   = (NEW_ADDRESS >> 8) & 0xFF
            addl   = NEW_ADDRESS & 0xFF
            sped   = make_sped(uart_baud=NEW_UART_BAUD, air_rate=NEW_AIR_RATE)
            chan   = NEW_CHANNEL
            option = make_option(fixed_mode=FIXED_MODE, fec=FEC_ON,
                                 tx_power_dbm=NEW_TX_POWER)

            print(f"[3] Writing new config...")
            print(f"    Packet: C0 {addh:02X} {addl:02X} {sped:02X} {chan:02X} {option:02X}")
            echo = write_config(ser, addh, addl, sped, chan, option, save=True)
            print(f"    Echo  : {' '.join(f'0x{b:02X}' for b in echo)}\n")

            # 4. Verify
            print("[4] Verifying written config...")
            raw2 = read_config(ser)
            decode_config(raw2)

            # 5. Back to normal mode (M0=0, M1=0)
            print("[5] Switching back to normal (transparent) mode...")
            set_mode(h, m0=0, m1=0)
            print("    Done. Module ready.\n")

    finally:
        lgpio.gpiochip_close(h)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nAborted.")
    except Exception as e:
        print(f"\nError: {e}")
