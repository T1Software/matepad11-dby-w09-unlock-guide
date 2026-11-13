# What we tried that did not work, and why

Kept deliberately, so nobody else burns hours on the same dead ends. Every item here was tested on this specific device (`DBY-W09`, starting at `3.0.0.216 C432`).

---

## 1. `adb reboot edl` on HarmonyOS 3.0.0.216

**Result:** command exits 0, tablet reboots, comes straight back into HarmonyOS. No `05C6` device on USB at any point.

**Why:** Huawei removed the EDL trigger from this build. It works on HOS 2.x and it works again after downgrading. This is the single fact that makes the downgrade mandatory.

**Workaround:** none. Downgrade to 2.0.0.278.

---

## 2. `fastboot oem edl` while locked

**Result:**

```
fastboot oem edl              FAILED (remote: 'Command not allowed')
fastboot getvar all           FAILED (remote: 'Command not allowed')
fastboot flashing get_unlock_ability   FAILED
fastboot oem get-bootinfo     (bootloader) INFO locked      <- only this works
```

**Why:** the locked ABL whitelists exactly one command. Everything that could actually help is refused.

**Workaround:** none. Unlocking the ABL requires EDL, which requires the downgrade.

---

## 3. Volume keys at power-on → "QRD mode"

Holding Volume Up + Volume Down while plugging in produces:

```
USB\VID_05C6&PID_F000&REV_0419
BusReportedDeviceDesc : KONA-QRD _SN:96B459EF
Service               : USBSTOR
FriendlyName          : USB Mass Storage Device
Model                 : Linux File-Stor Gadget
PartitionStyle        : RAW      OperationalStatus: No Media
```

**Why this is a trap:** the vendor ID `05C6` looks right and the QRD string looks encouraging. But `PID_F000` is Qualcomm's reference-design **mass-storage gadget**, exported by HarmonyOS's own Linux kernel — the SoC is already running Huawei code. EDL is `PID_9008`, and only the boot ROM produces it.

`No Media` means it exports nothing. There is nothing to read and nothing to flash.

---

## 4. Passive "engineering cable" (D+/D−)

Three variants were built and tested on this unit:

| Variant | Tablet state |
|---|---|
| D+ / D− open (both cut) | booted normally, no `9008` |
| D+ shorted to D− | booted normally, no `9008` |
| D+ and D− both to GND | booted normally, no `9008` |

In all three the tablet powered from the cable and booted, which proves the boot ROM did sample the data lines during power-on — and did not care.

**Why:** the download-mode strap on this build is not wired to USB line state. It is a GPIO or the test pads. Cable tricks are a Kirin/VCOM technique that does not transfer to this Qualcomm platform.

**Conclusion: do not build one.** It costs a cable and teaches you nothing.

---

## 5. Stock recovery

```
Restart
Factory reset
Wipe cache
Safe mode
```

There is **no** "Update mode", no "Memory card/OTG update", no "Apply update from storage". The recovery cannot install anything.

**Why it matters:** it rules out the whole `dload` path on this build, which is otherwise the cleanest way to flash firmware without a PC.

---

## 6. HiSuite version matters more than anything

| Build | Update screen | Rollback offered? |
|---|---|---|
| 10.1.0.550 OVE | "You're now using the latest official version" | no |
| 11.0.0.650 OVE | same | no |
| **14.0.0.380 OVE** | full version switcher | **yes** |

HiSuite 10.1 and 11 do not expose a rollback UI for this device at all. HiSuite 14 does. This was discovered the hard way after two installs and a lot of wasted time.

---

## 7. HiSuite Proxy with an offline package

The proxy (`ProfessorJTJ/HISuite-Proxy` V3.3.0) installs its root CA and intercepts HiSuite's update index correctly. It cannot be used here because:

- its `Set PKG` buttons stay `Enabled=False` with no ROM row selected
- there is **no valid RomID** for `DBY-LGRP4-OVS 102.0.0.278` — Firm Finder, BaseArchive and the Downgrade DB all contain zero DBY-W09 entries (the databases are frozen at 2021-era snapshots)
- without a RomID its request handler throws `Dictionary get_Item(TKey)` and returns zero bytes

**Also:** Windows Defender quarantines `HiSuite Proxy V3.exe` as `Trojan:Script/Wacatac.B!ml`. That is a heuristic false positive — the tool genuinely installs a root certificate and MITMs TLS, which is exactly what the heuristic looks for. It is legitimate for its purpose, but you should know what you are allowing.

**Use HiSuite 14 instead.**

---

## 8. Firmware from Huawei's own CDN

```
update.dbankcdn.com      does not resolve from this network
consumer-tkb.huawei.com  resolves, connection refused
```

The GitHub mirror `ngojclee/matepad11-hos42-google` (releases `binaries` and `firmware`) is the working source. Packages over 2 GB are split into parts.

---

## 9. ProjectMenu (`*#*#2846579*#*#`)

The package exists: `/system/app/HwProjectMenu/HwProjectMenu.apk`.

Every entry point is gated:

```
/data/data/... ProjectMenuActivity          requires android.permission.SECURITY_ACTIVITY
.entry.SoftwareUpgradeEntry                 same
.job.QrCodeInfoActivity                     same
.job.BatteryCharge$BatteryChargeActivity    same
.EmptyLicenseActivity                       same
```

`SECURITY_ACTIVITY` is declared by `com.huawei.mmitest` with `signature|privileged` protection. Shell (`uid=2000`) can never hold it. There is **no launcher-visible activity** in the package.

The secret-code receiver is registered but shell cannot fire the broadcast:

```
am broadcast -a android.provider.Telephony.SECRET_CODE -d android_secret_code://2846579
  SecurityException: not allowed to send broadcast ... uid=2000
```

And even if you got in, the APK contains only battery-charge animations, a QR code display, a screen saver and a cloud-firmware dialog. **There is no download-mode or EDL option** — that is a Kirin-era feature.

---

## 10. `fastboot` writes

Fastboot worked for `getvar` and then died:

```
fastboot reboot    FAILED (AdbWriteEndpointSync failed: semaphore timeout (121))
fastboot continue  FAILED (same)
fastboot oem reboot FAILED (same)
```

The bootloader was fine; the USB bulk endpoint had stalled. **Power + Volume Down for 30 s** resets it. Power alone does nothing in fastboot mode.

**Consequence: use EDL for every write.** EDL never failed once across ~30 operations at 35–40 MB/s.

---

## 11. GPT rewrite for 4.2

The 4.2 layout wants to resize several partitions:

```
version            32 MiB  ->  576 MiB
recovery_ramdisk   32 MiB  ->   36 MiB
erecovery_ramdisk  32 MiB  ->   36 MiB
super            7528 MiB  -> 7336 MiB
userdata       108840 MiB  ->    0 MiB     <- firmware regrows
secdata          1632 MiB  ->    0 MiB     <- encrypted keystore
```

`secdata` going to zero length is undocumented anywhere. It holds keystore data; if the firmware does not recreate it correctly you get a device that boots but cannot store keys — no lock screen, no fingerprint, no encryption.

**Skipped.** Only two partitions actually block the flash (`recovery_ramdisk`, `erecovery_ramdisk`), and leaving them on the HOS 2 layout costs only Huawei recovery — which is worth less than EDL anyway.

---

## 12. `kptools repack` after patching the kernel

```bash
kptools -p -i kernel -k kpimg -s KEY -o kernel_patched   # patches the kernel
kptools repack boot_stock.img                            # repacks the ORIGINAL kernel
```

The resulting image reports `patched=false`. The `repack` subcommand uses the boot image's own embedded kernel, not your patched file.

**Correct form — one step:**

```bash
kptools -p -i boot_stock.img -k kpimg -s KEY -o boot_patched.img
```

---

## 13. APatch modules without a metamodule

APatch dropped built-in module mounting in 10977. Installing `gms_mtg12.zip` on a fresh APatch does nothing observable — the module appears in the list, the files exist under `/data/adb/modules/`, and `/system/product/priv-app/GmsCore/` stays empty.

**Required order:**

```
1. install magic_mount (+ AndroidPatch userspace)  -> reboot
2. install gms module                              -> reboot
```

The metamodule must be registered at `/data/adb/metamodule/` before anything else can mount.

---

## 14. Launcher database writes without a reboot

Pushing a modified `launcher.db` and force-stopping the launcher is not enough. The running process holds its own copy and writes it back on exit — your changes silently vanish.

**Only a full reboot makes the launcher re-read the database.**

Also: while the launcher is running it holds the file, so `rm` + `cp` can leave a `-journal` that resurrects the old content. Remove `launcher.db*` (including `-journal`, `-wal`, `-shm`) with the launcher stopped.
