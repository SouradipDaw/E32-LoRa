#!/usr/bin/env python3
"""
E32-900T30D — Sends pre-generated packets from packets.txt using the
protocol e32_file_rx.py expects:

    [0xAA] [SEQ_HI] [SEQ_LO] [LEN] [...payload (<=29B)...] [CRC8]

- HEADER packet: SEQ=0xFFFF, payload = struct.pack(">HI", total_chunks, file_size)
  Sent 3x up front so the receiver knows what to expect even if one is lost.
- DATA packets: SEQ = 0 .. total_chunks-1, payload = chunk text bytes.

Reserved SEQ values (control sentinels, alongside data seqs 0..0xFFFB):
    0xFFFF  HEADER      TX -> RX
    0xFFFE  NACK        RX -> TX   payload = packed 2-byte missing seq numbers
    0xFFFD  NACK_END    RX -> TX   empty payload, end of one NACK batch-set
    0xFFFC  DONE        RX -> TX   empty payload, receiver has everything

After the initial full send, this script switches to listening: it waits
up to LISTEN_TIMEOUT seconds for the receiver to reply. If DONE arrives (or
nothing arrives at all), the transfer is considered finished. If NACK(s) +
NACK_END arrive, only the requested chunks are resent, and the script goes
back to listening. This repeats for up to MAX_ROUNDS rounds.

Reads packets.txt (produced by make_packets_seq.py):
    TOTAL:<n>
    SIZE:<file_size>
    0:<chunk text>
    1:<chunk text>
    ...
"""

import time
import struct
import serial
import lgpio

MOD_A = dict(port="/dev/ttyAMA2", baud=9600, M0=17, M1=27, AUX=22, name="A(TX)")

PACKETS_FILE        = "photo_packets.txt"
INTER_PACKET_DELAY  = 0.5    # validated safe floor is 0.35s at this air rate — don't go lower
CONTROL_GAP         = 0.2    # extra spacing for the header packets
HEADER_SEQ          = 0xFFFF
NACK_SEQ            = 0xFFFE
NACK_END_SEQ        = 0xFFFD
DONE_SEQ            = 0xFFFC

LISTEN_TIMEOUT      = 6.0    # seconds to wait for a NACK/DONE reply before giving up
MAX_ROUNDS          = 5      # max retransmission rounds after the initial send

# ---------- E32 control (unchanged from validated version) ----------

def set_mode(h, cfg, mode):
    m = {"normal": (0, 0), "wakeup": (0, 1), "power": (1, 0), "sleep": (1, 1)}
    lgpio.gpio_write(h, cfg["M0"], m[mode][0])
    lgpio.gpio_write(h, cfg["M1"], m[mode][1])
    time.sleep(0.02)

def wait_aux(h, cfg, timeout=3.0):
    t0 = time.time()
    while lgpio.gpio_read(h, cfg["AUX"]) == 0:
        if time.time() - t0 > timeout:
            raise TimeoutError(f"{cfg['name']}: AUX timeout")
        time.sleep(0.005)

def read_config(h, ser, cfg):
    set_mode(h, cfg, "sleep")
    wait_aux(h, cfg)
    time.sleep(0.05)
    ser.reset_input_buffer()
    ser.write(bytes([0xC1, 0xC1, 0xC1]))
    time.sleep(0.15)
    resp = ser.read(6)
    print(f"[{cfg['name']}] CFG: {resp.hex()}")
    return resp

def crc8(data):
    c = 0
    for b in data:
        c ^= b
    return c

def build_packet(seq, payload):
    hdr = bytes([0xAA, (seq >> 8) & 0xFF, seq & 0xFF, len(payload)])
    body = hdr + payload
    return body + bytes([crc8(body)])

class FrameParser:
    """Parses [0xAA][SEQ_HI][SEQ_LO][LEN][payload...][CRC8] frames."""
    def __init__(self):
        self.state = 0
        self.buf = bytearray()
        self.length = 0
        self.bad = 0

    def feed(self, data):
        frames = []
        for b in data:
            if self.state == 0:
                if b == 0xAA:
                    self.buf = bytearray([b])
                    self.state = 1
            elif self.state == 1:
                self.buf.append(b)
                self.state = 2
            elif self.state == 2:
                self.buf.append(b)
                self.state = 3
            elif self.state == 3:
                self.buf.append(b)
                self.length = b
                self.state = 4
            elif self.state == 4:
                self.buf.append(b)
                if len(self.buf) == 4 + self.length + 1:
                    frame = bytes(self.buf)
                    body, crc = frame[:-1], frame[-1]
                    if crc8(body) == crc:
                        seq = (frame[1] << 8) | frame[2]
                        payload = frame[4:-1]
                        frames.append((seq, payload))
                    else:
                        self.bad += 1
                    self.state = 0
                    self.buf = bytearray()
        return frames

def load_packets(path):
    """Returns (total_chunks, file_size, [(seq, chunk_text), ...] sorted by seq)."""
    total_chunks = None
    file_size = None
    packets = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line:
                continue
            if line.startswith("TOTAL:"):
                total_chunks = int(line.split(":", 1)[1])
                continue
            if line.startswith("SIZE:"):
                file_size = int(line.split(":", 1)[1])
                continue
            seq_str, chunk_text = line.split(":", 1)
            packets.append((int(seq_str), chunk_text))
    packets.sort(key=lambda p: p[0])
    return total_chunks, file_size, packets

# ---------- Main ----------

def main():
    total_chunks, file_size, packets = load_packets(PACKETS_FILE)
    if total_chunks is None or file_size is None:
        raise ValueError("packets.txt is missing TOTAL: or SIZE: header lines — "
                          "regenerate it with make_packets_seq.py")
    if total_chunks != len(packets):
        print(f"[!] Warning: header says {total_chunks} chunks but {len(packets)} were loaded.")

    packet_lookup = {seq: chunk_text for seq, chunk_text in packets}

    print(f"Loaded {len(packets)} packets from {PACKETS_FILE}  (file_size={file_size}B)")

    h = lgpio.gpiochip_open(0)
    for cfg in (MOD_A,):
        lgpio.gpio_claim_output(h, cfg["M0"])
        lgpio.gpio_claim_output(h, cfg["M1"])
        lgpio.gpio_claim_input(h, cfg["AUX"])

    ser = serial.Serial(MOD_A["port"], baudrate=MOD_A["baud"], timeout=0.1)
    print("=== E32 Transmitter (packets.txt -> e32_file_rx.py protocol) ===")
    print(f"  TX: {MOD_A['name']} {MOD_A['port']}  "
          f"M0=GPIO{MOD_A['M0']} M1=GPIO{MOD_A['M1']} AUX=GPIO{MOD_A['AUX']}")
    read_config(h, ser, MOD_A)
    set_mode(h, MOD_A, "normal")
    wait_aux(h, MOD_A)

    def send(seq, payload=b""):
        pkt = build_packet(seq, payload)
        wait_aux(h, MOD_A)
        ser.write(pkt)
        time.sleep(INTER_PACKET_DELAY)

    def listen_for_reply():
        """Waits up to LISTEN_TIMEOUT for NACK(s)+NACK_END or DONE.
        Returns ('done', None) or ('nack', sorted_missing_seq_list) or ('silence', None)."""
        parser = FrameParser()
        requested = set()
        t0 = time.time()
        while time.time() - t0 < LISTEN_TIMEOUT:
            raw = ser.read(128)
            if not raw:
                continue
            for seq, payload in parser.feed(raw):
                if seq == DONE_SEQ:
                    return "done", None
                elif seq == NACK_SEQ:
                    for i in range(0, len(payload) - 1, 2):
                        (s,) = struct.unpack(">H", payload[i:i + 2])
                        requested.add(s)
                elif seq == NACK_END_SEQ:
                    return ("nack", sorted(requested)) if requested else ("silence", None)
        return ("nack", sorted(requested)) if requested else ("silence", None)

    try:
        print("Sending header (x3)...")
        header_payload = struct.pack(">HI", total_chunks, file_size)
        for _ in range(3):
            send(HEADER_SEQ, header_payload)
            time.sleep(CONTROL_GAP)

        print("Sending data chunks...")
        sent = 0
        for seq, chunk_text in packets:
            payload = chunk_text.encode("utf-8")
            assert len(payload) < 30, f"Packet #{seq} is {len(payload)} bytes — exceeds limit"
            send(seq, payload)
            sent += 1
            print(f"[TX] seq={seq}: {chunk_text}  ({len(payload)}B)")
            if seq % 200 == 0 or sent == len(packets):
                print(f"  sent {sent}/{len(packets)}  (seq={seq})")

        print(f"\nInitial round: all {sent} packets sent.")

        round_num = 0
        while round_num <= MAX_ROUNDS:
            print(f"Listening for receiver reply (up to {LISTEN_TIMEOUT}s)...")
            status, missing = listen_for_reply()

            if status == "done":
                print("Receiver confirmed DONE — transfer complete.")
                break
            if status == "silence":
                print("No reply from receiver — assuming transfer is finished.")
                break

            # status == "nack"
            round_num += 1
            if round_num > MAX_ROUNDS:
                print(f"[!] Reached MAX_ROUNDS ({MAX_ROUNDS}) — stopping.")
                break
            print(f"[Round {round_num}] Resending {len(missing)} requested chunk(s): "
                  f"{missing[:20]}{' ...' if len(missing) > 20 else ''}")
            for seq in missing:
                chunk_text = packet_lookup.get(seq)
                if chunk_text is None:
                    print(f"  [!] seq {seq} not found in {PACKETS_FILE}, skipping")
                    continue
                payload = chunk_text.encode("utf-8")
                send(seq, payload)
                print(f"[TX] seq={seq}: {chunk_text}  ({len(payload)}B)  [resend]")

        print("\nTransfer session finished.")
    except KeyboardInterrupt:
        print("\nInterrupted.")
    finally:
        ser.close()
        lgpio.gpiochip_close(h)

if __name__ == "__main__":
    main()
