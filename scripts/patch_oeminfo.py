#!/usr/bin/env python3
import shutil, sys

SRC = "backup/edl-<stamp>/lun0/oeminfo.bin"
DST = "backup/oeminfo_cn.bin"

buf = bytearray(open(SRC, "rb").read())
shutil.copyfile(SRC, SRC + ".orig")

def patch(off, new, slot=40):
    nb = new.encode()
    old = bytes(buf[off:off+len(nb)]).decode("ascii", "replace")
    print(f"  0x{off:06X}: {old!r} -> {new!r} ({len(nb)} bytes)")
    buf[off:off+len(nb)] = nb
    for i in range(len(nb), slot):
        if buf[off+i] == 0:
            break
        buf[off+i] = 0xFF

patch(0x011200, "all/cn")
patch(0x060200, "DBY-W09")

open(DST, "wb").write(buf)
orig = open(SRC, "rb").read()
diff = sum(1 for a, b in zip(orig, buf) if a != b)
print(f"\nwrote {DST}  ({len(buf)} B)  bytes changed: {diff}")
