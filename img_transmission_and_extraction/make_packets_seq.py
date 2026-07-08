#!/usr/bin/env python3
"""
Packetizer — splits a text file into <30-byte packets, saving them in the
same sequence/order that e32_file_rx.py expects to receive them.

Output format (packets.txt):
    TOTAL:<total_chunks>
    SIZE:<original_file_size_bytes>
    0:<chunk text>
    1:<chunk text>
    ...
    <total_chunks-1>:<chunk text>

Sequence numbers are 0-indexed to match e32_file_rx.py's data-packet SEQ
range (0 .. total_chunks-1, with 0xFFFF reserved as the HEADER sentinel).
TOTAL and SIZE together are exactly what the transmitter needs to build
the HEADER packet's payload: struct.pack(">HI", total_chunks, file_size).

NOTE: assumes ASCII input (true for hex-encoded data like
image_instructions.txt used elsewhere in this project) — a chunk boundary
could otherwise fall mid-character for multi-byte UTF-8 text.
"""

INPUT_FILE      = "photo_instructions.txt"
OUTPUT_FILE     = "photo_packets.txt"
MAX_CHUNK_BYTES = 29   # strictly under the 30-byte requirement

def main():
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        text = f.read()

    data = text.encode("utf-8")
    total_size = len(data)
    chunks = [data[i:i + MAX_CHUNK_BYTES] for i in range(0, total_size, MAX_CHUNK_BYTES)]
    total_chunks = len(chunks)

    if total_chunks > 0xFFFE:
        raise ValueError(f"Too many chunks ({total_chunks}) for a 16-bit sequence "
                          f"number with 0xFFFF reserved. Increase MAX_CHUNK_BYTES.")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as out:
        out.write(f"TOTAL:{total_chunks}\n")
        out.write(f"SIZE:{total_size}\n")
        for seq, chunk in enumerate(chunks):
            assert len(chunk) < 30, f"Chunk {seq} is {len(chunk)} bytes — exceeds limit"
            out.write(f"{seq}:{chunk.decode('utf-8')}\n")

    print(f"Input : {INPUT_FILE}  ({total_size} bytes)")
    print(f"Output: {OUTPUT_FILE}  ({total_chunks} packets, max {MAX_CHUNK_BYTES}B each, seq 0-{total_chunks-1})")

if __name__ == "__main__":
    main()
