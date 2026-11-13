#!/usr/bin/env python3
import argparse, os, re, struct, sys, zipfile

MAGIC = b"\x55\xAA\x5A\xA5"
ALIGN = 4
DATE_RE = re.compile(r"^\d{4}\.\d{2}\.\d{2}$")

def iter_entries(fh, total):
    pos = 0
    while pos < total - 24:
        fh.seek(pos)
        buf = fh.read(1 << 16)
        if not buf:
            break
        idx = buf.find(MAGIC)
        if idx < 0:
            break
        fh.seek(pos + idx)
        hdr = fh.read(0x50)
        if len(hdr) < 0x50:
            break
        hlen = struct.unpack_from("<I", hdr, 0x04)[0]
        size = struct.unpack_from("<I", hdr, 0x18)[0]
        date = hdr[0x1C:0x2C].decode("ascii", "replace").strip("\x00 ")
        time = hdr[0x2C:0x3C].decode("ascii", "replace").strip("\x00 ")
        name = hdr[0x3C:0x4C].decode("ascii", "replace").strip("\x00 ")
        if not DATE_RE.match(date):
            pos += idx + 1
            continue
        yield name, pos + idx, hlen, size
        nxt = pos + idx + hlen + size
        pos = (nxt + ALIGN - 1) // ALIGN * ALIGN

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("container")
    ap.add_argument("-o", "--out")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()

    if a.container.lower().endswith(".zip"):
        z = zipfile.ZipFile(a.container)
        inner = z.open("UPDATE.APP")
        total = z.getinfo("UPDATE.APP").file_size
        fh = inner
    else:
        fh = open(a.container, "rb")
        total = os.path.getsize(a.container)

    if a.list:
        print(f"{'type':<28}{'size':>12}{'MB':>8}  header")
        n = 0
        for name, off, hlen, size in iter_entries(fh, total):
            print(f"{name:<28}{size:>12}{size/1048576:>8.1f}  {hlen}")
            n += 1
        print(f"\n{n} entries")
        return

    os.makedirs(a.out, exist_ok=True)
    for name, off, hlen, size in iter_entries(fh, total):
        fh.seek(off + hlen)
        dst = os.path.join(a.out, name.lower() + ".img")
        with open(dst, "wb") as o:
            left = size
            while left:
                chunk = fh.read(min(1 << 20, left))
                if not chunk:
                    break
                o.write(chunk)
                left -= len(chunk)
        print(f"  -> {os.path.basename(dst):<34} {size}")

if __name__ == "__main__":
    main()
