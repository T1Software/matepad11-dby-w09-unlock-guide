# Huawei MatePad 11 (DBY-W09) — Unlock, Root, GMS & Debloat

A field-tested, reproducible procedure to take a **Huawei MatePad 11 (2021), model DBY-W09**, from a locked C432 HarmonyOS 3 tablet to:

- HarmonyOS 4.2.0.208 (C00 China) / Android 12
- Unlocked bootloader with working Qualcomm EDL access
- APatch kernel-level root
- Working Google Play Services + Play Store (systemless)
- English UI with a German QWERTZ physical keyboard
- ~56 Huawei packages removed and a clean home screen

Everything here was executed on real hardware. Every hash, offset and command in this document was verified against the device, not copied from another guide.

---

## Read this first

**This can permanently brick your tablet.** The failure modes are real:

- Writing the wrong `abl` image → no boot, no fastboot, no EDL
- Interrupting an EDL write mid-way → device drops into a Sahara error state
- Taking an OTA after unlocking → bootloader relocks and **your EDL escape hatch disappears**
- Flashing 4.2 while locked → cannot reach EDL from software at all, test points required

**There is no warranty, no recovery service, and no one to call.** If you cannot accept that, stop now.

Do not skip the backup step. It is the only thing that turns "bricked" into "inconvenient".

---

## Device facts (verified on this unit)

| Item | Value |
|---|---|
| Model | DBY-W09 (MatePad 11 2021) |
| SoC | Qualcomm Snapdragon 865 / SM8250 `kona` |
| Firehose CPU string | `SM8250:CD90-PH805-1A` |
| Storage | 128 GB UFS 3.1, Micron `KLUDG4UHDB-B2D1` |
| UFS geometry | 30 693 376 blocks × 4096 B, 6 LUNs |
| Starting firmware | `DBY-W09S 3.0.0.216(C432E2R2P1)` — HOS 3, Android 12 |
| Final firmware | `DBY-W09 4.2.0.208(C00E100)` — HOS 4.2, Android 12 |
| Sectors | 4096 B logical, 4096 B physical |
| Slot layout | A-only (no `_a`/`_b`) |

### Critical partition geometry

```
abl    LUN 4   offset 0x000c206000   sector 49670   1024 sectors    4 MiB
boot   LUN 4   offset 0x0010706000   sector 67334   24576 sectors  96 MiB
oeminfo LUN 0  offset 0x0000300000   sector 12288   24576 sectors  96 MiB
```

`abl` and `boot` both live on **LUN 4**. This is the single most important fact in the whole procedure — writing `abl` to LUN 0 destroys the tablet.

---

## Table of contents

1. [Prerequisites](#1-prerequisites)
2. [Why the path looks like this](#2-why-the-path-looks-like-this)
3. [Stage 0 — Downgrade to HarmonyOS 2](#3-stage-0--downgrade-to-harmonyos-2)
4. [Stage 1 — Enter EDL and back up everything](#4-stage-1--enter-edl-and-back-up-everything)
5. [Stage 2 — Unlock the bootloader](#5-stage-2--unlock-the-bootloader)
6. [Stage 3 — Convert region to C00](#6-stage-3--convert-region-to-c00)
7. [Stage 4 — Flash HarmonyOS 4.2](#7-stage-4--flash-harmonyos-42)
8. [Stage 5 — Root with APatch](#8-stage-5--root-with-apatch)
9. [Stage 6 — Google Play without GMS framework](#9-stage-6--google-play-without-gms-framework)
10. [Stage 7 — Debloat](#10-stage-7--debloat)
11. [Stage 8 — Home screen and status bar](#11-stage-8--home-screen-and-status-bar)
12. [Troubleshooting](#12-troubleshooting)
13. [Restore / undo](#13-restore--undo)
14. [Reference](#14-reference)

---

## 1. Prerequisites

### Hardware

| Item | Why |
|---|---|
| Windows 10/11 x64 PC | EDL tooling, firmware extraction |
| Reliable USB-C **data** cable | Not charge-only. A flaky cable kills EDL sessions |
| USB flash drive ≥ 8 GB + USB-C OTG adapter | Only if you go the dload route (Stage 0 alternative) |
| Multimeter | Verifying your own cables and continuity |

### Software

| Tool | Version used | Purpose |
|---|---|---|
| [Android platform-tools](https://developer.android.com/tools/releases/platform-tools) | 37.0.1 | adb / fastboot |
| [bkerler/edl](https://github.com/bkerler/edl) | V3.62 | Sahara + Firehose client |
| Python | 3.12 | runs `edl.py` |
| [Zadig](https://zadig.akeo.ie/) | 2.9 | binds WinUSB to the EDL device, **once per PC** |
| [7-Zip](https://www.7-zip.org/) or `tar` | — | firmware archives (`tar` handles `.rar` on Win10+) |
| HiSuite | **14.0.0.380_OVE** | the downgrade (see note) |

### Firmware files (with hashes)

From the GitHub mirror `ngojclee/matepad11-hos42-google`, releases `binaries` and `firmware`:

| File | Size | SHA-256 |
|---|---|---|
| `abl_hw865870unlock.elf` | 602 112 B | `552E96D2565627563B7F2B072F720EFD048ABDF11FA050959AEC55E7D3F0B79D` |
| `dbyprog_emmc_firehose` | 697 648 B | `A0E08A0A26B1356E04FB3B3097C70237A2E3E0861DBD1A99CAFBAB4F5ADC7C9D` |
| `update_full_base.zip` | 4 788 537 569 B | `65C6039F24F9BA9C040E1BA9CF050E1720BF37F9AB293DE7B16E7D004BC02213` |
| `update_full_cust_DBY-W09_all_cn.zip` | 379 357 B | `4D5C9D48942C92161776DCD6B2A82CC623BC7C5720AA9E5E23A1A5F05C6554C9` |
| `update_full_preload_DBY-W09_all_cn_R1.zip` | 840 016 077 B | `4C1A00658798D2EE5670FC6A7EF3E03C2AD5A380CA7CFF18A1B06DD9C409B17E` |
| `magic_mount.zip` (APatch metamodule) | 251 987 B | from `AndroidPatch/magic_mount` v0.2 |
| `MindTheGapps-12.1.0-arm64` | 230 MB | tag `MindTheGapps-12.1.0-arm64-20231025_200924` |

`update_full_base.zip` is >2 GB so it is published split into 4 parts; concat them in order and verify the hash before use.

> **Always verify hashes.** A truncated firmware download that flashes "almost completely" is one of the nastier ways to end up with a device that boots to a black screen.

---

## 2. Why the path looks like this

The order is not arbitrary. Each stage exists because the previous one is blocked.

```
HOS 3.0.0.216, locked
    │  adb reboot edl -> silently no-ops on this build
    │  fastboot oem edl -> "Command not allowed" (ABL is locked)
    │  fastboot getvar -> refused
    ▼
HOS 2.0.0.278          <- downgrade makes adb reboot edl work again
    │
    ▼
EDL (05C6:9008)        <- the only write path that exists while locked
    │
    ▼
backup everything      <- the undo button
    │
    ▼
write unlock ABL       <- now fastboot and EDL both work permanently
    │
    ▼
convert oeminfo        <- C432 device will not accept C00 firmware
    │
    ▼
flash HOS 4.2 C00      <- Android 12, the base GMS is built for
    │
    ▼
re-flash unlock ABL    <- 4.2 blocks adb reboot edl; EDL now only via fastboot oem edl
    │
    ▼
APatch root -> GMS -> debloat
```

**The single hardest constraint:** on HarmonyOS 3.0.0.216 there is *no software way* into EDL. We tested all of them:

| Method | Result on HOS 3.0.0.216 |
|---|---|
| `adb reboot edl` | no-op, boots back to system |
| `fastboot oem edl` | `Command not allowed` |
| `fastboot reboot edl` | unknown target |
| Volume keys at power-on | `05C6:F000` QRD mass-storage gadget — **not** EDL |
| Recovery menu | Restart / Factory reset / Wipe cache / Safe mode only |
| HiSuite rollback | not offered |
| HiSuite Proxy offline package | no valid RomID for 2.0.0.278 |
| Firm Finder / BaseArchive DB | zero DBY-W09 rows |
| ProjectMenu (`*#*#2846579#*#*`) | all activities gated on `SECURITY_ACTIVITY`, system-signature only |

Note the `05C6:F000` result — that is Qualcomm's QRD storage gadget, produced by HarmonyOS's own kernel, not by the boot ROM. It looks promising and is useless. Only `05C6:9008` is EDL.

A passive "engineering cable" was also built and tested (D+/D− cut, shorted, grounded to GND). None of the three produced `9008`. **Do not waste time on cables for this model.**

---

## 3. Stage 0 — Downgrade to HarmonyOS 2

Target: `DBY-W09S 2.0.0.278(C432E2R2P1)`

### 3.1 Install HiSuite 14.0.0.380 OVE

**Use HiSuite 14.0.0.380_OVE, not 10.1.0.550.** The older build does not offer the rollback at all — its Update screen only reports "You're now using the latest official version". HiSuite 14 is the one that actually performs the version switch on this device.

Download: <https://consumer.huawei.com/en/support/hisuite/>

### 3.2 The unsigned driver problem

HiSuite installs a driver `ew_usbccgpfilter.sys` (`oem61.inf`) that Windows 11 blocks under Core Isolation / Memory Integrity. When it fails to load, the **whole USB composite device** fails (`Code 39`) and the tablet disappears from USB entirely — no ADB, no MTP, nothing.

Fix, run as Administrator:

```powershell
pnputil /delete-driver oem61.inf /uninstall /force
```

Then unplug/replug the tablet. It re-enumerates with the in-box `usbccgp` driver and everything works.

> This removal is **not permanent** — reinstalling or repairing HiSuite puts it back. If the tablet vanishes from USB again after a HiSuite update, run the command again.

### 3.3 Downgrade

1. Enable HDB on the tablet: Settings → search `HDB` → allow HiSuite
2. Connect, enter the 8-digit code shown in the HiSuite app on the tablet
3. HiSuite → **Update** → switch to another version → `2.0.0.278`

**Field notes that saved hours:**

- **If the download fails with a network error, just restart HiSuite and try again.** The CDN throttles and drops long transfers. There is nothing wrong with the connection — retry works.
- HiSuite deletes the package after a failed attempt. If you have a verified copy, drop it back into `%USERPROFILE%\Documents\HiSuite\ROM\` to skip the 4.2 GB download.
- While HiSuite holds the device, `adb` sees nothing. That is expected — `hdbtransport.exe` owns the interface.
- Verify afterwards: `adb shell getprop ro.build.display.id` → `DBY-W09S 2.0.0.278(C432E2R2P1)`

**This wipes all user data.**

---

## 4. Stage 1 — Enter EDL and back up everything

### 4.1 Verify the downgrade fixed EDL

```powershell
adb reboot edl
```

Within ~10 seconds Windows Device Manager shows:

```
Qualcomm HS-USB QDLoader 9008
USB\VID_05C6&PID_9008
```

If `getprop ro.boot.flash.locked` was `1` before and this works, you are in business.

### 4.2 Bind WinUSB once per PC

The EDL device has no driver. `edl.py` will fail with `NotImplementedError: Operation not supported` until you fix that.

1. Run **Zadig**
2. Options → **List All Devices**
3. Select `QUSB_BULK_CID:0412_SN:...` (USB ID must read `05C6 9008`)
4. Target = **WinUSB**
5. **Replace Driver**

> Selecting the wrong device here will break a keyboard or mouse until reboot. Check the USB ID.

### 4.3 Install the EDL client

```powershell
git clone https://github.com/bkerler/edl.git
cd edl
pip install -r requirements.txt
```

### 4.4 Sanity check

```powershell
$env:PYTHONIOENCODING='utf-8'
$env:PYTHONUTF8='1'
python edl.py printgpt --memory=ufs --lun=0 --loader=dbyprog_emmc_firehose
```

Expected output includes:

```
CPU detected: SM8250:CD90-PH805-1A
Serial: 0x96b459ef
prod_name: KLUDG4UHDB-B2D1
total_blocks: 30693376
Parsing Lun 0:  GPT Table:  (40 partitions)
```

> The UTF-8 environment variables are not optional — `edl.py`'s progress bar uses Unicode block characters and crashes on a cp1252 console.

### 4.5 Full backup

The single most important step. Use `rl` (read whole LUN, skip what you do not need):

```powershell
foreach ($lun in 0..5) {
  python edl.py rl "backup\lun$lun" --memory=ufs --lun=$lun `
      --skip=userdata,cache,log,rawdump,secdata --loader=dbyprog_emmc_firehose
}
```

That produced **87 files / 11.07 GB** on this device in about 5 minutes at ~40 MB/s.

Verify the critical ones:

| File | Must be |
|---|---|
| `lun4\abl.bin` | exactly **4 194 304 B**, starts `7F 45 4C 46` (ELF) |
| `lun4\boot.bin` | exactly **100 663 296 B**, starts `ANDROID!` |
| `lun0\oeminfo.bin` | exactly **100 663 296 B** |
| GPT dumps | `gpt_main0..5.bin` + `gpt_backup0..5.bin` present |

Then **copy the whole folder to a second disk**. One copy is not a backup.

---

## 5. Stage 2 — Unlock the bootloader

The mechanism: replace the signed `abl` with an unlocked engineering ABL over EDL. Secure boot itself is untouched — the unlocked ABL simply stops refusing flash commands.

### 5.1 Write

```powershell
python edl.py w abl abl_hw865870unlock.elf --memory=ufs --lun=4 --loader=dbyprog_emmc_firehose
```

Expect: `Wrote ... to sector 49670.`

### 5.2 Read back and compare — **do not skip**

```powershell
python edl.py r abl abl_after.bin --memory=ufs --lun=4 --loader=dbyprog_emmc_firehose
```

The **first 602 112 bytes** of `abl_after.bin` must hash to:

```
552E96D2565627563B7F2B072F720EFD048ABDF11FA050959AEC55E7D3F0B79D
```

Only reset the device when this matches. If it does not, you can still write `lun4\abl.bin` back — you are still in EDL.

### 5.3 Reset and verify

```powershell
python edl.py reset --resetmode=reset --loader=dbyprog_emmc_firehose
```

After boot:

```powershell
adb shell getprop ro.boot.flash.locked       # 0
adb shell getprop ro.boot.verifiedbootstate  # orange
adb shell getprop ro.boot.vbmeta.device_state # unlocked
fastboot oem get-bootinfo                    # (bootloader) INFO unlocked
fastboot getvar unlocked                     # unlocked: yes
```

### 5.4 Known trap: fastboot hangs

On this device `fastboot` sometimes accepts `getvar` and then fails every subsequent command with:

```
AdbWriteEndpointSync failed: The semaphore timeout period has expired. (121)
```

The bootloader has not crashed — the USB bulk endpoint has. **Power + Volume Down held for ~30 s** forces a reset out of it. `fastboot reboot` will *not* work in this state, and the Power button alone does nothing (fastboot mode has no ACPI handling).

Because of this, **prefer EDL over fastboot for every write.** EDL was rock-solid at 35–40 MB/s across dozens of operations; fastboot timed out twice.

---

## 6. Stage 3 — Convert region to C00

A C432 device refuses C00 firmware. The region identity lives in `oeminfo` and is a **9-byte edit**.

### 6.1 Locate the fields

```powershell
# on the backed-up oeminfo.bin
# 0x011200 : "hw/eu"     -> "all/cn"
# 0x060200 : "DBY-W09S"  -> "DBY-W09"
```

Both are fixed-width slots padded with `FF`, so longer replacements fit if you repad.

### 6.2 Patch a copy, never the original

```python
data = bytearray(open('oeminfo.bin','rb').read())

def patch(buf, off, new, slot=40):
    nb = new.encode()
    buf[off:off+len(nb)] = nb
    for i in range(len(nb), slot):
        if buf[off+i] == 0:
            break
        buf[off+i] = 0xFF

patch(data, 0x011200, 'all/cn')
patch(data, 0x060200, 'DBY-W09')
open('oeminfo_cn.bin','wb').write(data)
```

Result: exactly **7 bytes changed** (`hw/eu`→`all/cn` is +1 byte, plus the dropped `S`).

### 6.3 Write and verify

```powershell
python edl.py w oeminfo oeminfo_cn.bin --memory=ufs --lun=0 --loader=dbyprog_emmc_firehose
python edl.py r oeminfo oeminfo_after.bin --memory=ufs --lun=0 --loader=dbyprog_emmc_firehose
# SHA-256 of oeminfo_after.bin must equal oeminfo_cn.bin
```

After reboot the device still boots and reports `C00` for `ro.hw_sc.cversion`.

> Memory-tuning related settings reset during this — USB debugging turned off, so re-enable it.

---

## 7. Stage 4 — Flash HarmonyOS 4.2

### 7.1 Extract the images

The `.zip` contains `UPDATE.APP`, a Huawei container format. Parse, don't guess:

```powershell
python extract_updateapp.py UPDATE.APP --list
python extract_updateapp.py UPDATE.APP     -o work\base
python extract_updateapp.py UPDATE_cust.APP    -o work\cust
python extract_updateapp.py UPDATE_preload.APP -o work\preload
```

`super` comes split into two parts (u32 size limit). Merge with overlay semantics, **not** concatenation:

```powershell
python sparse.py work\base\super.img work\base\super_part1.img -o work\super_full.img
# -> 7 692 353 536 bytes (7336 MiB)
```

### 7.2 Check fit before writing anything

Only **two** partitions are too small on the HOS 2 layout:

| Partition | 4.2 image | Current partition |
|---|---|---|
| `recovery_ramdisk` | 36 MiB | 32 MiB |
| `erecovery_ramdisk` | 36 MiB | 32 MiB |

Everything else fits, including `super` (7336 MiB into 7528 MiB).

**Two options:**

**(a) Skip the GPT rewrite — recommended.** Do not flash the two ramdisk partitions. Normal boot works; Huawei recovery is left inconsistent. Since EDL is a far better recovery than Huawei's, this costs nothing real. No repartitioning, no risk to `userdata`/`secdata`.

**(b) Rewrite the GPT.** Fully correct layout, but it resizes `secdata` from 1632 MiB to **zero** and `userdata` to zero-length for the firmware to regrow. `secdata` holds encrypted keystore data — if the firmware does not recreate it correctly you get a device that boots but cannot hold keys. This is the riskiest operation in the entire tutorial, worse than the ABL write.

This tutorial uses **(a)**.

### 7.3 Stage and flash

Never flash `abl` from the 4.2 package — it is the **stock** ABL and would relock the bootloader.

Write order matters: small pass first so a fundamental problem shows up cheaply.

```powershell
# LUN 4 — 16 partitions, ~340 MB. Do this first.
python edl.py w <part> stage\lun4\<part>.img --memory=ufs --lun=4 --loader=dbyprog_emmc_firehose
# LUN 1 — xbl, xbl_config
# LUN 0 — 23 partitions, ~8.2 GB, super is the big one
```

On this device: LUN 4 = 1 m 32 s, LUN 1 = 3 s, LUN 0 = 5 m 19 s. Zero failures.

After the writes, **re-verify the unlock ABL is still in place** (nothing should have touched it):

```powershell
python edl.py r abl abl_check.bin --memory=ufs --lun=4 --loader=dbyprog_emmc_firehose
# first 602112 bytes must still hash to 552E96D2...
```

Then reset. First boot of a full firmware replacement takes a few minutes.

### 7.4 Verify

```powershell
adb shell getprop ro.build.display.id   # DBY-W09 4.2.0.208(C00E100)
adb shell getprop ro.build.version.release   # 12
adb shell getprop ro.boot.flash.locked       # 0
```

### 7.5 Critical: EDL entry changes on 4.2

```
adb reboot edl      -> NO LONGER WORKS on 4.2
fastboot oem edl    -> WORKS (because ABL is unlocked) -> OKAY, then 05C6:9008
```

This is why every guide says to re-flash the unlock ABL before first boot. If you flash 4.2 with a stock ABL, you end up on a locked 4.2 with **no EDL path at all** — test points become the only option.

---

## 8. Stage 5 — Root with APatch

APatch patches the **kernel inside `boot`**, not the ramdisk. On this device `boot.img` has `ramdisk_size = 0` and the ramdisk lives in a separate partition.

### 8.1 Why patch on the device

`kptools` ships inside the APatch APK as `libkptools.so`, and the `kpimg` payload is in `assets/kpimg`. You can patch entirely on-device — no PC-side toolchain.

```bash
AP=/data/app/~~.../me.bmax.apatch-.../lib/arm64
cp $AP/libkptools.so /data/local/tmp/kptools
chmod 755 /data/local/tmp/kptools
cp /data/local/tmp/ap.apk ... # unzip assets/kpimg out of the APK
```

### 8.2 Patch — one step, not two

```bash
/data/local/tmp/kptools -p -i /sdcard/boot_stock.img \
    -k /data/local/tmp/apatch/assets/kpimg \
    -s <YOUR_SUPERKEY> -o /data/local/tmp/boot_apatch.img
```

> **Trap:** `kptools -p -i kernel` followed by `kptools repack` produces an image containing the **original** kernel — `-l` reports `patched=false`. The one-step form above does extract → patch → repack correctly.

Verify before flashing:

```bash
/data/local/tmp/kptools unpack boot_apatch.img
/data/local/tmp/kptools -i kernel -l
#   patched=true
#   [kpimg]  version=0xd09  arch=arm64  superkey=<redacted>
```

A warning like `no CFI failure handler symbol` is informational on this kernel — it only matters for Android 13+ GKI with `CONFIG_CFI_CLANG`.

### 8.3 Flash and verify

```powershell
python edl.py w boot stage\boot_apatch.img --memory=ufs --lun=4 --loader=dbyprog_emmc_firehose
python edl.py r boot boot_readback.bin --memory=ufs --lun=4 --loader=dbyprog_emmc_firehose
# SHA-256 must match boot_apatch.img
python edl.py reset --resetmode=reset --loader=dbyprog_emmc_firehose
```

```powershell
adb shell su -c id
# uid=0(root) gid=0(root) groups=0(root) context=u:r:magisk:s0
```

The `magisk:s0` SELinux context is correct — it means the kernel patch applies its own policy rather than just handing out uid 0.

### 8.4 In the APatch app

- Top card must read **Working** with the KernelPatch version
- **AndroidPatch must also be installed** — it is a separate userspace layer (`apd`) that handles module mounting. Without it, modules install and do nothing.

---

## 9. Stage 6 — Google Play without GMS framework

HarmonyOS has no GMS framework. You add it **systemless** so `/system` stays untouched (AVB would otherwise break).

### 9.1 APatch has no built-in mount system

Since APatch 10977 there is no built-in module mounting. You must install a **metamodule** first.

| Module | Source |
|---|---|
| `magic_mount.zip` | `github.com/AndroidPatch/magic_mount` release `0.2` |

Install via APatch → Modules → install from storage → **reboot** (mandatory before any other module).

Verify registration:

```
/data/adb/metamodule/libmagic_mount.so
/data/adb/metamodule/magic_mount.lua
/data/adb/modules/magic_mount
```

### 9.2 Build the GMS module

Take these from MindTheGapps 12.1 arm64 — and only these. `Velvet` (245 MB) and `SetupWizard` cause a setup loop on a ROM not provisioned for it.

```
system/product/priv-app/GmsCore/GmsCore.apk                        105 MB
system/product/priv-app/Phonesky/Phonesky.apk                      57 MB
system/product/priv-app/GooglePartnerSetup/GooglePartnerSetup.apk
system/system_ext/priv-app/GoogleServicesFramework/…apk
system/product/etc/permissions/*.xml
system/system_ext/etc/permissions/*.xml
system/product/etc/sysconfig/google*.xml
system/product/etc/default-permissions/*.xml
system/product/etc/security/fsverity/gms_fsverity_cert.der
system/product/framework/com.google.android.dialer.support.jar
system/product/lib/libjni_latinimegoogle.so
system/product/lib64/libjni_latinimegoogle.so
```

Module structure — `module.prop` and `customize.sh` at the **zip root**, files under `system/`, **LF line endings**:

```properties
id=gms_mtg12
name=MindTheGapps 12.1 (arm64)
version=v1.0
versionCode=1
author=MindTheGapps
description=Play Services + Play Store + GSF for HarmonyOS 4.2 (Android 12), systemless
```

```sh
#!/system/bin/sh
SKIPUNZIP=0
set_perm_recursive $MODPATH/system/product/priv-app 0 0 0755 0644
set_perm_recursive $MODPATH/system/system_ext/priv-app 0 0 0755 0644
```

Result: a ~78 MB zip. Install via APatch → Modules → reboot.

### 9.3 Verify the mount actually landed

```powershell
adb shell su -c "ls /system/product/priv-app/GmsCore/"
adb shell pm list packages | grep -iE 'vending|gms|gsf'
adb shell dumpsys package com.android.vending | grep versionName
```

The `codePath` proves it is your module and not system:

```
com.android.vending        /system/product/priv-app/Phonesky
com.google.android.gms     /system/product/priv-app/GmsCore
com.google.android.gsf     /system/system_ext/priv-app/GoogleServicesFramework
```

### 9.4 What works and what does not

| Works | Does not work |
|---|---|
| Play Store installs and updates apps | Play Protect shows "not certified" |
| Play Services API for most apps | Play Integrity fails |
| FCM push (`mtalk.google.com:5228`) | Banking apps requiring integrity |
| Contacts / calendar sync | — |
| Netflix Widevine L1 | — |

**If Play Store shows a blank screen** after a reboot, the mount failed. Fix: APatch → Modules → toggle `gms_mtg12` off and on → reboot. It is not broken, the overlay just did not apply.

---

## 10. Stage 7 — Debloat

`pm disable-user` marks a package disabled for user 0. It deletes nothing and frees no space, but it is instantly reversible with `pm enable`. `pm uninstall --user 0` hides the app entirely for the user while the APK stays in `/system` — restore with `cmd package install-existing <pkg>`.

### 10.1 Disable

```powershell
$pkgs = @(
  # OTA — prevents the bootloader relocking. Do this first.
  'com.huawei.android.hwouc',
  'com.huawei.hms.dupdateengine',
  # stores / video / music / kids
  'com.huawei.magazine','com.huawei.gamebox','com.vmall.client',
  'com.huawei.wallet','com.huawei.wallet.facard','com.unionpay.tsmservice',
  'com.tencent.qqlivehuawei','com.sohu.sohuvideo.emplayer',
  'com.huawei.himovie','com.huawei.himovie.local',
  'com.huawei.himovie.partner1','com.huawei.himovie.partner2',
  'com.huawei.hmos.himovie.fa','com.huawei.music','com.huawei.music.local',
  'com.huawei.tips','com.huawei.android.tips','com.huawei.kidsmode',
  # telemetry / diagnostics
  'com.huawei.hiview','com.huawei.hiviewtunnel','com.huawei.android.chr',
  'com.huawei.hwdetectrepair','com.huawei.hwdiagnosis','com.huawei.recsys',
  'com.huawei.contentsensor',
  # assistant / search / cards / smart home
  'com.huawei.search','com.huawei.searchservice','com.huawei.intelligent',
  'com.huawei.ohos.suggestion','com.huawei.hicard',
  'com.huawei.associateassistant','com.huawei.meetime',
  'com.huawei.smarthome','com.huawei.ohos.smarthome',
  # clone / life / member / my huawei / cloud
  'com.hicloud.android.clone','com.huawei.lives','com.huawei.mycenter',
  'com.huawei.phoneservice','com.huawei.hicloud',
  # mobile network stack (Wi-Fi-only tablet: no SIM slot)
  'com.android.phone','com.android.stk','com.android.cellbroadcastreceiver',
  'com.android.cellbroadcastservice','com.android.mms.service',
  'com.android.simappdialog','com.android.ons','com.huawei.numberidentity',
  'com.huawei.remotepassword','org.codeaurora.ims',
  'com.qualcomm.qti.telephonyservice','com.qualcomm.qcrilmsgtunnel',
  'com.android.incallui','com.android.server.telecom','com.android.emergency'
)
foreach ($p in $pkgs) { adb shell "pm disable-user --user 0 $p" }
```

### 10.2 Uninstall for user 0

```powershell
foreach ($p in @('com.huawei.hicloud','com.huawei.android.findmyphone',
                 'com.huawei.contacts','com.android.mms',
                 'com.huawei.filemanager','com.huawei.filemanager.fa',
                 'com.huawei.appmarket')) {
  adb shell "pm uninstall --user 0 $p"
}
```

### 10.3 Packages that refuse

```
com.huawei.parentcontrol             "not allowed to disable this package"
com.android.carrierconfig            "not allowed to disable this package"
com.huawei.hidisk                    DELETE_FAILED_INTERNAL_ERROR on uninstall
```

`hidisk` (Cloud Drive) is protected; `pm disable-user` works on it even though uninstall does not.

### 10.4 Do not touch

| Package | Why |
|---|---|
| `com.android.providers.telephony` | owns the SMS/MMS DB — disabling causes crash loops |
| `com.huawei.hwid` | Huawei ID; needed if any Huawei app signs in |
| `com.huawei.android.pushagent` | HMS push for any remaining Huawei app |
| `com.huawei.iaware` | resource AI — disabling **increases** battery drain |
| `com.huawei.behaviorauth` | may be wired into lock screen |
| `com.huawei.systemmanager`, `.systemserver`, `.harmonyos.foundation` | core |
| `com.huawei.android.launcher` | home screen |

---

## 11. Stage 8 — Home screen and status bar

### 11.1 The launcher database

Huawei's launcher keeps the home layout in an SQLite DB:

```
/data/user_de/0/com.huawei.android.launcher/databases/launcher.db
```

Two tables matter: `favorites6x5` is what this build actually renders (6 columns × 5 rows), `favorites_simpleui` is a parallel HOS layout. `container = -100` is the home screen, `-101` is the dock.

Pull it with root, edit `cellX` / `cellY`, push back with the **original owner**:

```powershell
adb shell "su -c 'am force-stop com.huawei.android.launcher'"
adb shell "su -c 'rm -f /data/user_de/0/com.huawei.android.launcher/databases/launcher.db*'"
adb push launcher_new.db /sdcard/l.db
adb shell "su -c 'cp /sdcard/l.db /data/user_de/0/com.huawei.android.launcher/databases/launcher.db && chown u0_a80:u0_a80 <path> && chmod 660 <path> && rm -f /sdcard/l.db'"
adb reboot
```

> **You must reboot.** Force-stopping the launcher is not enough — it keeps its copy in memory and rewrites the DB on exit. Only a full boot re-reads it.

Back up the original first: `launcher.db.orig` next to the new one.

### 11.2 Status bar — hide the SIM icon

After disabling telephony, SystemUI keeps drawing a no-SIM icon with an exclamation mark. There is no SIM slot, so it is pure noise:

```powershell
adb shell "settings put secure icon_blacklist 'sim,nosim,mobile,airplane'"
adb shell "su -c 'pkill -f com.android.systemui'"   # applies without reboot
```

Persists across reboots. Undo: `settings delete secure icon_blacklist`.

### 11.3 Language vs keyboard layout

These are independent, which is what you usually want:

```powershell
# UI language
adb shell "su -c 'settings put system system_locales en-US'"
adb shell "su -c 'setprop persist.sys.locale en-US'"
# reboot required
```

For a **physical** keyboard, the layout is separate. On the C00 build the Settings UI hides the physical-keyboard page, but the activity exists — launch it directly:

```powershell
adb shell "am start -a android.settings.HARD_KEYBOARD_SETTINGS"
```

It lists every connected keyboard with a layout picker. All 57 layouts ship in `/system/priv-app/InputDevices/InputDevices.apk` (`res/raw/keyboard_layout_<name>.kcm`) — German QWERTZ included. Selecting one writes `keyboard_layout_german` into `/data/system/input-manager-state.xml`.

---

## 12. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `edl.py`: `NotImplementedError: Operation not supported` | no WinUSB binding on `05C6:9008` | Zadig → WinUSB |
| Tablet vanishes from USB entirely | `oem61.inf` failed to load under Memory Integrity (Code 39) | `pnputil /delete-driver oem61.inf /uninstall /force` |
| `fastboot` fails every command with `semaphore timeout (121)` | USB bulk endpoint died | hold **Power + Volume Down 30 s** to reset |
| Power button does nothing in fastboot | fastboot has no ACPI handling | same as above |
| `adb devices` empty, device present as `12D1:107D` | HiSuite/HDB owns the interface | close HiSuite, kill `hdbtransport`, restart adb server |
| `adb reboot edl` no-ops | HarmonyOS 3.0.0.216 and 4.x block it | on 2.0.278 it works; on 4.2 use `fastboot oem edl` |
| `edl.py printgpt` crashes on progress bar | cp1252 console | `$env:PYTHONIOENCODING='utf-8'` |
| HiSuite download fails with network error | CDN throttling | **just restart HiSuite and retry** |
| HiSuite offers no rollback | wrong HiSuite version | use **14.0.0.380_OVE** |
| 4.2 flash: "version check failed" | `oeminfo` still C432 | redo Stage 3 |
| APatch modules install but mount nothing | metamodule missing, or AndroidPatch not installed | install `magic_mount` **and** AndroidPatch, reboot between |
| Play Store blank after reboot | magic_mount overlay did not apply | toggle module off/on in APatch, reboot |
| `su` works over adb but not in apps | Shell granted root conflicts with module installer (`os error 2/5/22`) | revoke Shell's root in APatch → Superuser |
| Home layout changes revert | wrote DB without rebooting | reboot; launcher caches in memory |
| `kptools repack` output reports `patched=false` | patched kernel then repacked the original | use `-p -i boot.img` one-step form |

### Emergency: device in Sahara error state

If `edl.py` dies mid-transfer the loader can end up in an error state (`Mode detected: error`). The device does not respond to EDL until reset:

**Hold Power 20–30 s.** It boots normally. Your partitions are unchanged unless the write was interrupted *during* the data phase — in which case restore from backup (stage 13).

---

## 13. Restore / undo

### Restore a single partition

```powershell
python edl.py w <part> backup\edl-<stamp>\lun<N>\<part>.bin --memory=ufs --lun=<N> --loader=dbyprog_emmc_firehose
```

### Restore the bootloader (undo the unlock)

```powershell
python edl.py w abl backup\edl-<stamp>\lun4\abl.bin --memory=ufs --lun=4 --loader=dbyprog_emmc_firehose
python edl.py reset --resetmode=reset --loader=dbyprog_emmc_firehose
# flash.locked returns to 1
```

### Undo root

```powershell
python edl.py w boot backup\edl-<stamp>\lun4\boot.bin --memory=ufs --lun=4 --loader=dbyprog_emmc_firehose
```

Then uninstall the APatch app.

### Undo debloat

```powershell
adb shell "pm list packages -d" | ForEach-Object {
  $p = $_ -replace 'package:',''
  adb shell "pm enable $p"
}
adb shell cmd package install-existing com.huawei.hicloud   # etc.
```

**Note:** this re-enables the OTA packages too. Re-disable `com.huawei.android.hwouc` and `com.huawei.hms.dupdateengine` immediately afterwards.

---

## 14. Reference

### Final verified state

```
build          DBY-W09 4.2.0.208(C00E100)   Android 12
bootloader     unlocked   flash.locked=0   verifiedbootstate=orange
EDL entry      fastboot oem edl -> 05C6:9008
root           APatch 0.13.9 / KernelPatch 0.13.9   su -> uid=0
Google         GmsCore 21.48.15, Phonesky 28.8.17, GSF 12-7567768
modules        magic_mount (metamodule), gms_mtg12
UI             English (en-US) + German QWERTZ physical keyboard
OTA            disabled (hwouc, dupdateengine)
debloat        ~56 packages disabled, 7 uninstalled-for-user
backup         11.07 GB / 87 files, two disks, hash-verified
```

### Partition table (LUN 0 / LUN 4, abbreviated)

```
LUN 0  ssd persist nvme misc bsp_info reserved1 oeminfo bootfail_info rrecord
       cache frp log reserved3 eng_system eng_vendor erecovery erecovery_ramdisk
       erecovery_vendor recovery recovery_ramdisk recovery_vendor ramdisk
       erecovery_vbmeta recovery_vbmeta vbmeta_system vbmeta_vendor vbmeta_odm
       vbmeta_cust vbmeta_hw_product patch kpatch metadata reserved2 fw_ufsdev
       preas preavs super version preload userdata
LUN 1  xbl xbl_config
LUN 2  reserved4
LUN 3  ALIGN_TO_128K_1 cdt ddr
LUN 4  aop tz hyp modem bluetooth abl dsp keymaster boot devcfg qupfw vbmeta
       dtbo uefisecapp featenabler devinfo dip apdp limits rawdump storsec
       uefivarstore secdata
LUN 5  ALIGN_TO_128K_2 modemst1 modemst2 fsg fsc
```

### Credits

- [bkerler/edl](https://github.com/bkerler/edl) — Sahara/Firehose client
- [bmax121/APatch](https://github.com/bmax121/APatch) — KernelPatch root
- [AndroidPatch/magic_mount](https://github.com/AndroidPatch/magic_mount) — APatch metamodule
- [MindTheGapps](https://github.com/MindTheGapps) — GApps 12.1 arm64
- ngojclee, TheBula97, faxcon, scoolo (4PDA) — DBY-W09 rebranding & root documentation
- `fanyantao4110/HUAWEI_MatePad11_Tool_Kit_GUI` — confirmed the LUN 4 geometry independently

### Licence

CC BY-NC-SA 4.0 for this document. Firmware and tool binaries belong to their respective owners and are not redistributed here.
