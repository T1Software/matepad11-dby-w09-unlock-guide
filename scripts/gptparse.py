#!/usr/bin/env python3
import struct, sys

BLOCK = 45056
SECTOR = 4096

def parse_block(buf, base):
    h = base + 0x1000
    if buf[h:h+8] != b"EFI PART":
        return None
    num   = struct.unpack_from("<I", buf, h+80)[0]
    esize = struct.unpack_from("<I", buf, h+84)[0]
    out = []
    for i in range(num):
        o = base + 0x2000 + i*esize
        if o + 128 > len(buf) or buf[o:o+16] == b"\x00"*16:
            continue
        first = struct.unpack_from("<Q", buf, o+32)[0]
        last  = struct.unpack_from("<Q", buf, o+40)[0]
        name  = buf[o+56:o+128].decode("utf-16-le", "replace").split("\x00")[0]
        out.append((name, first, last))
    return out

buf = open(sys.argv[1], "rb").read()
for lun in range(len(buf)//BLOCK):
    parts = parse_block(buf, lun*BLOCK)
    if not parts:
        continue
    print(f"\n=== LUN{lun}  ({len(parts)} partitions)")
    for name, f, l in sorted(parts, key=lambda x: x[1]):
        print(f"  {name:<26} {f:>10}..{l:<10} {(l-f+1)*SECTOR/1048576:>8.1f} MiB")
