# Verified commands & hashes

Quick-reference card. Everything here was executed successfully on DBY-W09.

## Environment

```powershell
$PY = 'python'
$LOADER = 'dbyprog_emmc_firehose'
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONUTF8 = '1'
```

## EDL entry

| Firmware | Command | Result |
|---|---|---|
| HOS 2.0.278 | `adb reboot edl` | `05C6:9008` |
| HOS 3.0.0.216 | *(none)* | impossible from software |
| HOS 4.2 C00 | `fastboot oem edl` | `05C6:9008` |

## Partition read / write

```powershell
# read one partition
python edl.py r  <name> <out.bin>  --memory=ufs --lun=<N> --loader=$LOADER
# write one partition
python edl.py w  <name> <in.bin>   --memory=ufs --lun=<N> --loader=$LOADER
# read whole LUN, skipping big ones
python edl.py rl <dir>             --memory=ufs --lun=<N> --skip=userdata,cache,log,rawdump,secdata --loader=$LOADER
# GPT table
python edl.py printgpt             --memory=ufs --lun=<N> --loader=$LOADER
# reset
python edl.py reset --resetmode=reset --loader=$LOADER
```

## Hashes

| Artifact | SHA-256 |
|---|---|
| `abl_hw865870unlock.elf` | `552E96D2565627563B7F2B072F720EFD048ABDF11FA050959AEC55E7D3F0B79D` |
| `dbyprog_emmc_firehose` | `A0E08A0A26B1356E04FB3B3097C70237A2E3E0861DBD1A99CAFBAB4F5ADC7C9D` |
| `update_full_base.zip` | `65C6039F24F9BA9C040E1BA9CF050E1720BF37F9AB293DE7B16E7D004BC02213` |
| `update_full_cust_DBY-W09_all_cn.zip` | `4D5C9D48942C92161776DCD6B2A82CC623BC7C5720AA9E5E23A1A5F05C6554C9` |
| `update_full_preload_DBY-W09_all_cn_R1.zip` | `4C1A00658798D2EE5670FC6A7EF3E03C2AD5A380CA7CFF18A1B06DD9C409B17E` |

## Geometry

```
abl       LUN 4   sector 49670   1024 sectors    4 MiB
boot      LUN 4   sector 67334   24576 sectors  96 MiB
oeminfo   LUN 0   sector 12288   24576 sectors  96 MiB
super     LUN 0   sector 536064  1878016 sectors 7336 MiB (4.2 image)
```

## Boot-state checks

```powershell
adb shell getprop ro.boot.flash.locked        # 0 = unlocked
adb shell getprop ro.boot.verifiedbootstate   # orange = unlocked
adb shell getprop ro.boot.vbmeta.device_state # unlocked
fastboot oem get-bootinfo                     # (bootloader) INFO unlocked
fastboot getvar unlocked                      # unlocked: yes
adb shell su -c id                            # uid=0
```

## Common fixes

```powershell
# USB composite device dead (Code 39)
pnputil /delete-driver oem61.inf /uninstall /force

# adb blind because HiSuite holds the device
Get-Process hdbtransport,hwtransport,HiSuite | Stop-Process -Force
adb kill-server ; adb start-server

# hide SIM icon after disabling telephony
adb shell "settings put secure icon_blacklist 'sim,nosim,mobile,airplane'"
adb shell "su -c 'pkill -f com.android.systemui'"

# English UI
adb shell "su -c 'settings put system system_locales en-US'"
adb shell "su -c 'setprop persist.sys.locale en-US'"

# physical keyboard layout picker (hidden from Settings UI on C00)
adb shell "am start -a android.settings.HARD_KEYBOARD_SETTINGS"
```
