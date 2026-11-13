"""Tidy the home screen and include ADB Wi-Fi.

Preserves every app currently on the screen (Camera, Edge, Gallery, T1 Todi,
ADB Wi-Fi, Calendar, Calculator, Notes, Notepad, Weather, Email, APatch,
Settings, Wallpaper Engine, Clock, Recorder, Compass, Themes, Call of Duty).
"""
import sqlite3, shutil

SRC = r'C:\Users\bargo\Desktop\Matepad11\logs\launcher2.db'
OUT = r'C:\Users\bargo\Desktop\Matepad11\backup\launcher\launcher_new.db'

shutil.copyfile(SRC, OUT)
c = sqlite3.connect(OUT)
c.row_factory = sqlite3.Row
cur = c.cursor()

home = {}
for r in c.execute("select _id, title from favorites6x5 where container=-100 order by _id"):
    home.setdefault(r['title'], r)

print("on screen:", sorted(home))

layout = [
    ['Camera',    'Gallery', 'Clock',    'Calendar', 'Calculator', 'Notes'],
    ['Edge',      'T1 Todi', 'Notepad',  'Recorder', 'Compass',    'Weather'],
    ['ADB Wi-Fi', 'APatch',  'Settings', 'Themes',   'Wallpaper Engine', 'Email'],
    ['Call of Duty', None,   None,       None,       None,         None],
]

placed, missing = [], []
for y, row in enumerate(layout):
    for x, t in enumerate(row):
        if not t:
            continue
        r = home.get(t)
        if not r:
            missing.append(t)
            continue
        cur.execute("update favorites6x5 set screen=0, cellX=?, cellY=? where _id=?", (x, y, r['_id']))
        placed.append(t)

print(f"\nplaced {len(placed)}, missing {missing}")

unplaced = sorted(set(home) - set(placed))
if unplaced:
    print("NOT placed (left where they are):", unplaced)

# dock compact
dock = list(c.execute("select _id from favorites6x5 where container=-101 order by cellX"))
for i, d in enumerate(dock):
    cur.execute("update favorites6x5 set cellX=? where _id=?", (i, d['_id']))

c.commit()

print("\n--- HOME ---")
for r in c.execute("select cellY,cellX,title from favorites6x5 where container=-100 order by cellY,cellX"):
    print(f"  r{r[0]} c{r[1]}  {r[2]}")

print("\n--- DOCK ---")
for r in c.execute("select cellX,title from favorites6x5 where container=-101 order by cellX"):
    print(f"  c{r[0]}  {r[1]}")

c.execute("VACUUM"); c.commit(); c.close()
print(f"\nwrote {OUT}")
