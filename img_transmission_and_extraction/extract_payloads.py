#!/usr/bin/env python3
"""
Extracts payload bytes from a packets-format text file (either the
original packets.txt from make_packets_seq.py, or received_packets.txt
from e32_file_rx.py) and reassembles them, in SEQ order, into a plain
output file.

Accepted input format (extra lines are ignored):
    TOTAL:<total_chunks>
    SIZE:<file_size>
    <seq>:<chunk text>
    <seq>:<chunk text>
    ...
    MISSING:<count>                 (optional, ignored here)
    MISSING_SEQS:<comma list>       (optional, ignored here)

Notes:
- Lines are matched by their "<int>:" prefix, so TOTAL/SIZE/MISSING/
  MISSING_SEQS header lines are naturally skipped without special-casing
  (they don't start with a plain integer followed by ':').
- Input file may have entries in arrival order (e32_file_rx.py) or
  sorted order (make_packets_seq.py) — output is always written in
  SEQ order 0..total_chunks-1 regardless of the file's line order.
- Missing sequence numbers are written as empty (0 bytes), matching the
  behaviour of e32_file_rx.py's own reconstruction step.
"""

INPUT_FILE  = "received_packets.txt"
OUTPUT_FILE = "extracted_payload.txt"

def main():
    total_chunks = None
    file_size = None
    chunks = {}

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
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
            if line.startswith("MISSING:") or line.startswith("MISSING_SEQS:"):
                continue  # summary lines, not data

            seq_str, _, chunk_text = line.partition(":")
            if not seq_str.isdigit():
                continue  # not a data line, skip defensively
            seq = int(seq_str)
            if seq not in chunks:           # first occurrence wins on duplicates
                chunks[seq] = chunk_text.encode("utf-8")

    if total_chunks is None:
        raise ValueError(f"{INPUT_FILE} is missing a TOTAL: header line — "
                          "can't determine expected chunk count.")

    missing = [s for s in range(total_chunks) if s not in chunks]

    with open(OUTPUT_FILE, "wb") as out:
        for seq in range(total_chunks):
            out.write(chunks.get(seq, b""))

    written = sum(len(chunks.get(s, b"")) for s in range(total_chunks))
    print(f"Input : {INPUT_FILE}")
    print(f"  total_chunks={total_chunks}  "
          f"expected_size={file_size if file_size is not None else 'unknown'}B")
    print(f"  {len(chunks)}/{total_chunks} chunks present, {len(missing)} missing")
    if missing:
        preview = missing[:20]
        print(f"  missing seqs: {preview}{' ...' if len(missing) > 20 else ''}")
    print(f"Output: {OUTPUT_FILE}  ({written} bytes written)")

if __name__ == "__main__":
    main()
