#!/usr/bin/env python3
"""
E32-900T30D Configuration Utility
----------------------------------
Usage:
  python3 e32_config.py --port /dev/serial0 --m0 17 --m1 27 --aux 22 read
  python3 e32_config.py --port /dev/serial0 --m0 17 --m1 27 --aux 22 write
  python3 e32_config.py --port /dev/ttyUSB0 --m0 23 --m1 24 --aux 25 read

Default write target: addr=0x0000, ch=0x06 (868MHz), 9600 baud, 2.4kbps air, transparent
"""

import argparse
import time
import serial
import lgpio

SPED_TABLE = {
    # UART baud
    "uart_baud": {0: 1200, 1: 2400, 2: 4800, 3: 9600,
                  4: 19200, 5: 38400, 6: 57600, 7: 115200},
    # Air data rate
    "air_rate":  {0: "0.3k", 1: "1.2k", 2: "2.4k", 3: "4.8k",
                  4: "9.6k", 5: "19.2k", 6: "19.2k", 7: "19.2k"},
    # Parity
    "parity":    {0: "8N1", 1: "8O1", 2: "8E1", 3: "8N1"},
}
OPTION_TABLE = {
    "tx_mode":    {0: "Transparent", 1: "Fixed"},
    "io_drive":   {0: "TXD push-pull / AUX push-pull",
                   1: "TXD open-drain / AUX open-drain"},
    "wake_time":  {k: f"{(k+1)*250}ms" for k in range(8)},
    "fec":        {0: "Off", 1: "On"},
    "tx_power":   {0: "30dBm", 1: "27dBm", 2: "24dBm", 3: "21dBm"},
}

def decode_sped(sped: int):
    parity   = (sped >> 6) & 0x03
    uart_b   = (sped >> 3) & 0x07
    air_r    = (sped >> 0) & 0x07
    return {
        "parity":    SPED_TABLE["parity"][parity],
        "uart_baud": SPED_TABLE["uart_baud"][uart_b],
        "air_rate":  SPED_TABLE["air_rate"][air_r],
    }

def decode_option(opt: int):
    tx_mode   = (opt >> 7) & 0x01
    io_drive  = (opt >> 6) & 0x01
    wake_time = (opt >> 3) & 0x07
    fec       = (opt >> 2) & 0x01
    tx_power  = (opt >> 0) & 0x03
    return {
        "tx_mode":   OPTION_TABLE["tx_mode"][tx_mode],
        "io_drive":  OPTION_TABLE["io_drive"][io_drive],
        "wake_time": OPTION_TABLE["wake_time"][wake_time],
        "fec":       OPTION_TABLE["fec"][fec],
        "tx_power":  OPTION_TABLE["tx_power"][tx_power],
    }

def freq_mhz(chan: int) -> float:
    # 900MHz variant: base 900MHz + chan (MHz)
    return 900 + chan

def set_mode(h, m0, m1, mode: str):
    modes = {"normal":(0,0), "wakeup":(0,1), "power":(1,0), "sleep":(1,1)}
    lgpio.gpio_write(h, m0, modes[mode][0])
    lgpio.gpio_write(h, m1, modes[mode][1])
    time.sleep(0.02)

def wait_aux(h, aux, timeout=3.0):
    t = time.time()
    while lgpio.gpio_read(h, aux) == 0:
        if time.time() - t > timeout:
            raise TimeoutError("AUX timeout")
        time.sleep(0.005)

def cmd_read(h, ser, m0, m1, aux):
    set_mode(h, m0, m1, "sleep")
    wait_aux(h, aux)
    time.sleep(0.05)
    ser.reset_input_buffer()
    ser.write(bytes([0xC1, 0xC1, 0xC1]))
    time.sleep(0.15)
    resp = ser.read(6)
    if len(resp) < 6:
        print(f"[!] Short response ({len(resp)} bytes): {resp.hex()}")
        print("    Check wiring — M0/M1 must be HIGH for sleep mode.")
        return
    if resp[0] != 0xC0:
        print(f"[!] Unexpected response header: {resp.hex()}")
        return
    addr = (resp[1] << 8) | resp[2]
    sped = resp[3]
    chan  = resp[4]
    opt  = resp[5]
    print(f"\n{'='*40}")
    print(f"  Address : 0x{addr:04X}  ({addr})")
    print(f"  Channel : 0x{chan:02X}  → {freq_mhz(chan):.0f} MHz")
    s = decode_sped(sped)
    print(f"  SPED    : 0x{sped:02X}")
    print(f"    Parity    : {s['parity']}")
    print(f"    UART baud : {s['uart_baud']} bps")
    print(f"    Air rate  : {s['air_rate']} bps")
    o = decode_option(opt)
    print(f"  OPTION  : 0x{opt:02X}")
    print(f"    TX mode   : {o['tx_mode']}")
    print(f"    IO drive  : {o['io_drive']}")
    print(f"    Wake time : {o['wake_time']}")
    print(f"    FEC       : {o['fec']}")
    print(f"    TX power  : {o['tx_power']}")
    print(f"{'='*40}\n")

def cmd_write(h, ser, m0, m1, aux,
              addr=0x0000, sped=0x1A, chan=0x06, option=0x44):
    set_mode(h, m0, m1, "sleep")
    wait_aux(h, aux)
    time.sleep(0.05)
    addr_h = (addr >> 8) & 0xFF
    addr_l = addr & 0xFF
    cmd = bytes([0xC0, addr_h, addr_l, sped, chan, option])
    print(f"[CFG] Writing: {cmd.hex()}")
    ser.write(cmd)
    time.sleep(0.15)
    resp = ser.read(6)
    print(f"[CFG] Response: {resp.hex()}")
    if resp == cmd:
        print("[CFG] ✓ Config accepted (echo match)")
    else:
        print("[CFG] ✗ Response mismatch — re-check wiring/power")
    # verify
    print("[CFG] Verifying with read-back...")
    cmd_read(h, ser, m0, m1, aux)

def main():
    ap = argparse.ArgumentParser(description="E32-900T30D config tool")
    ap.add_argument("action", choices=["read", "write"])
    ap.add_argument("--port", default="/dev/serial0")
    ap.add_argument("--baud", type=int, default=9600)
    ap.add_argument("--m0",  type=int, default=17)
    ap.add_argument("--m1",  type=int, default=27)
    ap.add_argument("--aux", type=int, default=22)
    # write params
    ap.add_argument("--addr",   type=lambda x: int(x,0), default=0x0000)
    ap.add_argument("--sped",   type=lambda x: int(x,0), default=0x1A,
                    help="SPED byte (default 0x1A = 9600 baud, 2.4kbps, 8N1)")
    ap.add_argument("--chan",   type=lambda x: int(x,0), default=0x06,
                    help="Channel (default 0x06 = 906MHz)")
    ap.add_argument("--option", type=lambda x: int(x,0), default=0x44,
                    help="OPTION byte (default 0x44 = transparent, 30dBm)")
    args = ap.parse_args()

    h = lgpio.gpiochip_open(0)
    lgpio.gpio_claim_output(h, args.m0)
    lgpio.gpio_claim_output(h, args.m1)
    lgpio.gpio_claim_input(h, args.aux)

    ser = serial.Serial(args.port, baudrate=args.baud, timeout=1)
    print(f"Opened {args.port} @ {args.baud} baud")

    try:
        if args.action == "read":
            cmd_read(h, ser, args.m0, args.m1, args.aux)
        else:
            cmd_write(h, ser, args.m0, args.m1, args.aux,
                      addr=args.addr, sped=args.sped,
                      chan=args.chan, option=args.option)
    finally:
        set_mode(h, args.m0, args.m1, "normal")
        ser.close()
        lgpio.gpiochip_close(h)

if __name__ == "__main__":
    main()
