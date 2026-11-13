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
