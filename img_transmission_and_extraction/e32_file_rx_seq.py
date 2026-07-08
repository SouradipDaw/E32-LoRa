#!/usr/bin/env python3
"""
E32-900T30D — LoRa packet receiver with automatic missing-packet requests.

Packet format (unchanged):
    [0xAA] [SEQ_HI] [SEQ_LO] [LEN] [...payload (<=29B)...] [CRC8]

Reserved SEQ values (control sentinels, alongside data seqs 0..0xFFFB):
    0xFFFF  HEADER      TX -> RX   payload = struct.pack(">HI", total_chunks, file_size)
    0xFFFE  NACK        RX -> TX   payload = packed 2-byte missing seq numbers (<=14/pkt)
    0xFFFD  NACK_END    RX -> TX   empty payload, marks end of one NACK batch-set
    0xFFFC  DONE        RX -> TX   empty payload, "I have everything, you can stop"

Behavior:
- Listens for the HEADER, then data chunks, storing each unique SEQ the
  first time it's seen (duplicates ignored, no error).
- Every packet is logged to RECEIVED_PACKETS_FILE in the ORDER IT ARRIVED,
  tagged with its SEQ, using the same "seq:chunk_text" format
  make_packets_seq.py uses for the TX side's packets.txt.
- If no new packet arrives for IDLE_TIMEOUT seconds and chunks are still
  missing, the receiver compiles the missing SEQ list and sends NACK
  packet(s) + a NACK_END sentinel back to the transmitter, asking it to
  resend just those chunks. Repeats for up to MAX_ROUNDS rounds.
- Once complete (or rounds exhausted), a DONE packet is sent (best-effort)
  and the packet log + missing-count summary is written out.

NOTE: this only works if the transmitter is running the matching updated
e32_file_tx_seq.py, which listens for NACK/NACK_END/DONE after each send
round and resends only the requested chunks.
"""

import time
import struct
import serial
import lgpio

MOD_B = dict(port="/dev/ttyAMA4", baud=9600, M0=6, M1=7, AUX=19, name="B(RX)")

RECEIVED_PACKETS_FILE = "received_packets.txt"

HEADER_SEQ   = 0xFFFF
NACK_SEQ     = 0xFFFE
NACK_END_SEQ = 0xFFFD
DONE_SEQ     = 0xFFFC
CONTROL_SEQS = (HEADER_SEQ, NACK_SEQ, NACK_END_SEQ, DONE_SEQ)

IDLE_TIMEOUT       = 2.5   # seconds of silence before we ask for missing chunks
MAX_ROUNDS         = 5     # max number of "ask for missing chunks" rounds
INTER_PACKET_DELAY = 0.5   # matches TX side; don't go below the 0.35s validated floor
NACK_BATCH         = 14    # 14 seqs * 2B = 28B payload, under the 29B limit

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

def crc8(data):
    c = 0
    for b in data:
        c ^= b
    return c

def build_packet(seq, payload):
    hdr = bytes([0xAA, (seq >> 8) & 0xFF, seq & 0xFF, len(payload)])
    body = hdr + payload
    return body + bytes([crc8(body)])

class TransferComplete(Exception):
    pass

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
            if self.state == 0:                       # waiting for sync byte
                if b == 0xAA:
                    self.buf = bytearray([b])
                    self.state = 1
            elif self.state == 1:                      # SEQ_HI
                self.buf.append(b)
                self.state = 2
            elif self.state == 2:                      # SEQ_LO
                self.buf.append(b)
                self.state = 3
            elif self.state == 3:                      # LEN
                self.buf.append(b)
                self.length = b
                self.state = 4
            elif self.state == 4:                      # payload + CRC
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
                        # deliberately not printing per-failure here -- console
                        # flooding on every CRC failure previously escalated
                        # packet loss from ~12% to ~60%
                    self.state = 0
                    self.buf = bytearray()
        return frames

# ---------- NACK / DONE helpers ----------

def send_packet(h, ser, cfg, seq, payload=b""):
    pkt = build_packet(seq, payload)
    wait_aux(h, cfg)
    ser.write(pkt)
    time.sleep(INTER_PACKET_DELAY)

def request_missing(h, ser, cfg, missing):
    print(f"  -> requesting {len(missing)} missing chunk(s) from transmitter")
    for i in range(0, len(missing), NACK_BATCH):
        batch = missing[i:i + NACK_BATCH]
        payload = b"".join(struct.pack(">H", s) for s in batch)
        send_packet(h, ser, cfg, NACK_SEQ, payload)
    send_packet(h, ser, cfg, NACK_END_SEQ, b"")

def send_done(h, ser, cfg):
    send_packet(h, ser, cfg, DONE_SEQ, b"")

# ---------- Saving the packet log ----------

def save_received(path, total_chunks, file_size, arrival_log, missing):
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"TOTAL:{total_chunks if total_chunks is not None else 0}\n")
        f.write(f"SIZE:{file_size if file_size is not None else 0}\n")
        for seq, text in arrival_log:
            f.write(f"{seq}:{text}\n")
        f.write("\n")
        f.write(f"MISSING:{len(missing)}\n")
        if missing:
            f.write("MISSING_SEQS:" + ",".join(str(s) for s in missing) + "\n")

# ---------- Main ----------

def main():
    h = lgpio.gpiochip_open(0)
    for cfg in (MOD_B,):
        lgpio.gpio_claim_output(h, cfg["M0"])
        lgpio.gpio_claim_output(h, cfg["M1"])
        lgpio.gpio_claim_input(h, cfg["AUX"])

    ser = serial.Serial(MOD_B["port"], baudrate=MOD_B["baud"], timeout=0.1)

    print("=== E32 File Receiver (with NACK retransmission requests) ===")
    print(f"  RX: {MOD_B['name']} {MOD_B['port']}  "
          f"M0=GPIO{MOD_B['M0']} M1=GPIO{MOD_B['M1']} AUX=GPIO{MOD_B['AUX']}")

    set_mode(h, MOD_B, "normal")
    wait_aux(h, MOD_B)
    print("Listening for file transfer (Ctrl-C to stop early)...\n")

    parser = FrameParser()
    chunks = {}          # seq -> payload bytes, dedup store
    arrival_log = []     # [(seq, text), ...] first-arrival order, matches packets.txt format
    total_chunks = None
    file_size = None
    last_rx_time = time.time()
    round_num = 0

    try:
        while True:
            raw = ser.read(128)

            if raw:
                last_rx_time = time.time()
                for seq, payload in parser.feed(raw):
                    if seq == HEADER_SEQ:
                        if total_chunks is None:
                            total_chunks, file_size = struct.unpack(">HI", payload)
                            print(f"[HEADER] total_chunks={total_chunks}  file_size={file_size}B")
                        continue
                    if seq in CONTROL_SEQS:
                        continue  # NACK/NACK_END/DONE are RX->TX only, ignore if ever seen here

                    received_str = payload.decode("utf-8", errors="ignore")
                    print(f"Received packet {seq}: {received_str}")

                    if seq not in chunks:
                        chunks[seq] = payload
                        arrival_log.append((seq, received_str))

                    if total_chunks and len(chunks) % 50 == 0:
                        print(f"  received {len(chunks)}/{total_chunks} unique chunks  "
                              f"(CRC failures so far: {parser.bad})")

                if total_chunks and len(chunks) >= total_chunks:
                    print("\nAll chunks received.")
                    break
                continue

            # no bytes this read cycle -- check whether it's time to ask for missing chunks
            if total_chunks is None:
                continue
            if len(chunks) >= total_chunks:
                break
            if time.time() - last_rx_time >= IDLE_TIMEOUT:
                round_num += 1
                if round_num > MAX_ROUNDS:
                    print(f"\n[!] Gave up after {MAX_ROUNDS} request rounds.")
                    break
                missing = [s for s in range(total_chunks) if s not in chunks]
                print(f"\n[Round {round_num}] idle {IDLE_TIMEOUT}s — {len(missing)} chunk(s) missing")
                request_missing(h, ser, MOD_B, missing)
                last_rx_time = time.time()  # reset idle clock while TX catches up

    except KeyboardInterrupt:
        print("\nInterrupted.")

    missing = [] if total_chunks is None else [s for s in range(total_chunks) if s not in chunks]

    if total_chunks is not None and not missing:
        try:
            send_done(h, ser, MOD_B)
            print("Sent DONE to transmitter.")
        except TimeoutError:
            pass

    ser.close()
    lgpio.gpiochip_close(h)

    if total_chunks is None:
        print("\nNo header ever received — nothing to log.")
        return

    save_received(RECEIVED_PACKETS_FILE, total_chunks, file_size, arrival_log, missing)
    print(f"\nLogged {len(arrival_log)} packet(s) to {RECEIVED_PACKETS_FILE}")
    if missing:
        preview = missing[:20]
        print(f"[!] {len(missing)} chunk(s) still missing: {preview}"
              f"{' ...' if len(missing) > 20 else ''}")
    else:
        print("All chunks accounted for.")

if __name__ == "__main__":
    main()
