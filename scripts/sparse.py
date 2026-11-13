#!/usr/bin/env python3
import argparse, struct

SPARSE_MAGIC = 0xED26FF3A
CHUNK_RAW, CHUNK_FILL, CHUNK_DONT, CHUNK_CRC = 0xCAC1, 0xCAC2, 0xCAC3, 0xCAC4

def expand_overlay(parts, out_path):
    total_blocks = block_size = file_size = None

    with open(out_path, "wb") as out:
        for path in parts:
            with open(path, "rb") as f:
                hdr = f.read(28)
                magic, major, minor, fhsz, chdr, bsz, tblocks, tchunks, csum = \
                    struct.unpack("<IHHHHIIII", hdr)
                if magic != SPARSE_MAGIC:
                    raise SystemExit(f"{path}: not a sparse image")
                if total_blocks is None:
                    total_blocks = tblocks
                    block_size = bsz
                    file_size = total_blocks * block_size
                    out.truncate(file_size)
                print(f"  {path:<24} chunks={tchunks}  blocks={tblocks}")

                for _ in range(tchunks):
                    ch = f.read(12)
                    ctype, _, cblocks, ctotal = struct.unpack("<HHII", ch)
                    payload = ctotal - 12
                    if ctype == CHUNK_RAW:
                        out.seek(out.tell())
                        left = cblocks * block_size
                        while left:
                            b = f.read(min(1 << 20, left))
                            if not b:
                                break
                            out.write(b)
                            left -= len(b)
                    elif ctype == CHUNK_FILL:
                        val = f.read(4)
                        out.write(val * (cblocks * block_size // 4))
                    elif ctype == CHUNK_DONT:
                        out.seek(cblocks * block_size, 1)
                    elif ctype == CHUNK_CRC:
                        f.read(4)
    print(f"output {out_path}: {file_size} bytes ({file_size//1048576:.1f} MB)")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("parts", nargs="+")
    ap.add_argument("-o", "--out", required=True)
    a = ap.parse_args()
    expand_overlay(a.parts, a.out)
