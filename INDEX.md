# What is in this repository

| File | Contents |
|---|---|
| [README.md](README.md) | The full walkthrough, stages 0–8, troubleshooting, restore |
| [CHEATSHEET.md](CHEATSHEET.md) | Verified commands, hashes, geometry, one-liner fixes |
| [DEAD-ENDS.md](DEAD-ENDS.md) | 14 approaches that do not work on this device, and why |
| [SCRIPTS.md](SCRIPTS.md) | Source of every script used, with explanations |
| [scripts/](scripts/) | The same scripts as runnable files |

## Scripts

| File | Purpose |
|---|---|
| `scripts/extract_updateapp.py` | Parse Huawei `UPDATE.APP` container, list or extract |
| `scripts/sparse.py` | Merge split `super` sparse images (overlay, not concat) |
| `scripts/patch_oeminfo.py` | Convert region identity C432 → C00 (7 bytes) |
| `scripts/gptparse.py` | Parse `gpt_both0.bin` from the firmware package |
| `scripts/relayout.py` | Rewrite the HarmonyOS launcher home screen DB |
| `scripts/build_gms_module.py` | Build the APatch GMS module from MindTheGapps |

All are Python 3.10+ and dependency-free except `build_gms_module.py` (stdlib only too).

## Not included

No firmware, no loaders, no APKs, no backups. Those belong to their owners or to your device.
`README.md` section 1 lists exact filenames, sizes and SHA-256 hashes so you can fetch and
verify them yourself.

## Status of the guide

Executed end to end on one device: `DBY-W09`, 128 GB, starting on `DBY-W09S 3.0.0.216(C432E2R2P1)`.
If your starting firmware, region code or partition layout differs, re-read the relevant stage —
several steps depend on the exact build.
