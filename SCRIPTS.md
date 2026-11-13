# Software I wrote during this project

These scripts are what actually ran. Paths assume a project root like `C:\Users\<you>\Desktop\Matepad11`.

---

## extract_updateapp.py

Parses Huawei's `UPDATE.APP` container.

Format notes (the part everyone gets wrong):

- every entry starts with magic `55 AA 5A A5`
- `+0x04` u32 — header length, **varies per entry** (98, 126, 12386, 49250, 2030938) — do not clamp it
- `+0x18` u32 — payload size
- `+0x3C` 16B — type name, **truncated to 16 chars** (`vbmeta_hw_product` → `vbmeta_hw_produc`, `erecovery_ramdisk` → `erecovery_ramdis`)
- payload at magic + header length; next entry at payload + size, 4-byte aligned

```python
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
```

---

## sparse.py

Merges Huawei's split `super` image. The two parts are **overlays**, not concatenation:

```
part0:  [FILL][RAW ....][DONT .................]   data up to block N
part1:  [DONT .......][RAW ....................]   data from block N on
```

```python
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
```

---

## patch-oeminfo.py

Converts the region identity. Changes exactly 7 bytes.

```python
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
```

---

## gptparse.py

Reads the 4.2 package's `gpt_both0.bin`, which is 6 blocks of 45 056 bytes (11 sectors) — one per LUN. Primary header at `block+0x1000`, entries at `block+0x2000`.

```python
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
```

---

## relayout.py — launcher home screen

Edits `favorites6x5`. `container -100` = home, `-101` = dock. 6 columns.

```python
#!/usr/bin/env python3
import sqlite3, shutil, sys

SRC = "launcher_current.db"      # pulled from device
OUT = "launcher_new.db"

shutil.copyfile(SRC, OUT)
c = sqlite3.connect(OUT)
c.row_factory = sqlite3.Row
cur = c.cursor()

home = {}
for r in c.execute("select _id, title from favorites6x5 where container=-100"):
    home.setdefault(r["title"], r)

layout = [
    ["Camera",  "Gallery", "Clock",   "Calendar", "Calculator", "Notes"],
    ["Notepad", "Recorder","Compass", "Weather",  "Email",      "APatch"],
    ["Settings","Themes",  "Call of Duty", None,  None,         None],
]

for y, row in enumerate(layout):
    for x, title in enumerate(row):
        if not title or title not in home:
            continue
        cur.execute("update favorites6x5 set screen=0, cellX=?, cellY=? where _id=?",
                    (x, y, home[title]["_id"]))

for t in ("AppGallery", "SIM Toolkit"):        # icons whose apps are gone
    cur.execute("delete from favorites6x5 where title=? and container=-100", (t,))

dock = list(c.execute("select _id from favorites6x5 where container=-101 order by cellX"))
for i, d in enumerate(dock):
    cur.execute("update favorites6x5 set cellX=? where _id=?", (i, d["_id"]))

c.commit()
c.execute("VACUUM")
c.commit()
c.close()
print("wrote", OUT)
```

Then push and **reboot** — force-stopping the launcher is not enough:

```powershell
adb shell "su -c 'am force-stop com.huawei.android.launcher'"
adb shell "su -c 'rm -f /data/user_de/0/com.huawei.android.launcher/databases/launcher.db*'"
adb push launcher_new.db /sdcard/l.db
adb shell "su -c 'cp /sdcard/l.db /data/user_de/0/com.huawei.android.launcher/databases/launcher.db'"
adb shell "su -c 'chown u0_a80:u0_a80 /data/user_de/0/com.huawei.android.launcher/databases/launcher.db'"
adb shell "su -c 'chmod 660 /data/user_de/0/com.huawei.android.launcher/databases/launcher.db'"
adb reboot
```

---

## build-gms-module.py

Builds the APatch module zip from MindTheGapps. **LF line endings are mandatory** in `module.prop`.

```python
#!/usr/bin/env python3
import os, shutil, zipfile

MTG = "MindTheGapps-12.1.0-arm64.zip"
OUT = "gms-mtg12-apatch.zip"
WORK = "gms-module"

WANTED = [
    "system/product/priv-app/GmsCore/GmsCore.apk",
    "system/product/priv-app/Phonesky/Phonesky.apk",
    "system/product/priv-app/GooglePartnerSetup/GooglePartnerSetup.apk",
    "system/system_ext/priv-app/GoogleServicesFramework/GoogleServicesFramework.apk",
    "system/product/etc/permissions/privapp-permissions-google-product.xml",
    "system/system_ext/etc/permissions/privapp-permissions-google-system-ext.xml",
    "system/product/etc/permissions/com.google.android.dialer.support.xml",
    "system/product/etc/sysconfig/google.xml",
    "system/product/etc/sysconfig/google_build.xml",
    "system/product/etc/sysconfig/google-hiddenapi-package-allowlist.xml",
    "system/product/etc/sysconfig/d2d_cable_migration_feature.xml",
    "system/product/etc/default-permissions/default-permissions-google.xml",
    "system/product/etc/default-permissions/default-permissions-mtg.xml",
    "system/product/etc/security/fsverity/gms_fsverity_cert.der",
    "system/product/framework/com.google.android.dialer.support.jar",
    "system/product/lib/libjni_latinimegoogle.so",
    "system/product/lib64/libjni_latinimegoogle.so",
]

shutil.rmtree(WORK, ignore_errors=True)
with zipfile.ZipFile(MTG) as z:
    for w in WANTED:
        dst = os.path.join(WORK, w)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with z.open(w) as s, open(dst, "wb") as o:
            shutil.copyfileobj(s, o)

open(os.path.join(WORK, "module.prop"), "w", newline="\n").write(
    "id=gms_mtg12\n"
    "name=MindTheGapps 12.1 (arm64)\n"
    "version=v1.0\n"
    "versionCode=1\n"
    "author=MindTheGapps\n"
    "description=Play Services + Play Store + GSF for HarmonyOS 4.2, systemless\n"
)
open(os.path.join(WORK, "customize.sh"), "w", newline="\n").write(
    "#!/system/bin/sh\n"
    "SKIPUNZIP=0\n"
    "set_perm_recursive $MODPATH/system/product/priv-app 0 0 0755 0644\n"
    "set_perm_recursive $MODPATH/system/system_ext/priv-app 0 0 0755 0644\n"
)

with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
    z.write(os.path.join(WORK, "module.prop"), "module.prop")
    z.write(os.path.join(WORK, "customize.sh"), "customize.sh")
    for root, _, files in os.walk(os.path.join(WORK, "system")):
        for f in files:
            p = os.path.join(root, f)
            z.write(p, os.path.relpath(p, WORK).replace("\\", "/"))

print(OUT, os.path.getsize(OUT), "bytes")
```

---

## apatch-patch.sh — run on device

```sh
#!/system/bin/sh
# $1 = stock boot.img path, $2 = superkey
BOOT="$1"
SKEY="$2"

APK=$(pm path me.bmax.apatch | sed 's/package://')
APDIR=$(dirname "$APK")

# libkptools.so is the CLI
cp "$APDIR/lib/arm64/libkptools.so" /data/local/tmp/kptools
chmod 755 /data/local/tmp/kptools

# kpimg lives inside the APK assets
mkdir -p /data/local/tmp/apk
cp "$APK" /data/local/tmp/apk/ap.apk
cd /data/local/tmp/apk && unzip -o ap.apk assets/kpimg >/dev/null

# ONE STEP: extract -> patch -> repack
/data/local/tmp/kptools -p -i "$BOOT" \
    -k /data/local/tmp/apk/assets/kpimg \
    -s "$SKEY" \
    -o /data/local/tmp/boot_apatch.img

# verify
mkdir -p /data/local/tmp/chk && cd /data/local/tmp/chk
cp /data/local/tmp/boot_apatch.img .
/data/local/tmp/kptools unpack boot_apatch.img
/data/local/tmp/kptools -i kernel -l     # must say patched=true
```
