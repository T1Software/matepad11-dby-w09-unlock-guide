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
