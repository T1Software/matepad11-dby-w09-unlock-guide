@echo off
setlocal enabledelayedexpansion

set SDK=C:\Users\bargo\Desktop\Matepad11\android-sdk
set BT=%SDK%\build-tools\34.0.0
set PLATFORM=%SDK%\platforms\android-34\android.jar
set SRC=C:\Users\bargo\Desktop\Matepad11\adbtoggle
set OUT=%SRC%\build
set GEN=%OUT%\gen

if not exist "%BT%\aapt2.exe" ( echo ERROR: aapt2 missing & exit /b 1 )
if not exist "%PLATFORM%"      ( echo ERROR: android.jar missing & exit /b 1 )

if exist "%OUT%" rmdir /s /q "%OUT%"
mkdir "%OUT%" "%GEN%" 2>nul

echo [1/7] compile resources
"%BT%\aapt2.exe" compile --dir "%SRC%\res" -o "%OUT%\res.zip" || exit /b 1

echo [2/7] link + generate R.java
"%BT%\aapt2.exe" link -o "%OUT%\base.apk" -I "%PLATFORM%" --manifest "%SRC%\AndroidManifest.xml" -R "%OUT%\res.zip" --java "%GEN%" --auto-add-overlay || exit /b 1

echo [3/7] javac
javac -nowarn -source 11 -target 11 -classpath "%PLATFORM%" -d "%OUT%\classes" "%GEN%\com\t1software\adbtoggle\R.java" "%SRC%\src\com\t1software\adbtoggle\MainActivity.java" || exit /b 1

echo [4/7] d8 dex
set CLS=
for /r "%OUT%\classes" %%f in (*.class) do set CLS=!CLS! "%%f"
call "%BT%\d8.bat" --lib "%PLATFORM%" --min-api 26 --output "%OUT%" !CLS! || exit /b 1

echo [5/7] add dex to apk
pushd "%OUT%"
"%BT%\aapt.exe" add base.apk classes.dex || (popd & exit /b 1)
popd

echo [6/7] zipalign
"%BT%\zipalign.exe" -f 4 "%OUT%\base.apk" "%OUT%\aligned.apk" || exit /b 1

echo [7/7] sign
if not exist "%SRC%\keystore.jks" (
  echo generating test keystore
  keytool -genkeypair -keystore "%SRC%\keystore.jks" -alias adbtoggle -storepass adbtoggle -keypass adbtoggle -keyalg RSA -keysize 2048 -validity 10000 -dname "CN=ADB Wi-Fi Toggle, O=T1Software, C=DE" || exit /b 1
)
"%BT%\apksigner.bat" sign --ks "%SRC%\keystore.jks" --ks-pass pass:adbtoggle --key-pass pass:adbtoggle --out "%SRC%\adbtoggle.apk" "%OUT%\aligned.apk" || exit /b 1

echo.
echo DONE: %SRC%\adbtoggle.apk
dir /b "%SRC%\adbtoggle.apk"
