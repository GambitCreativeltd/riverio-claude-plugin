#!/usr/bin/env python3
"""Podcast beats: shot-by-shot "who is talking" audit of the 5 raw clips, to catch VOICE MIX-UPS
(the video model finishes one person's line in the other person's voice, usually at short interjections).

usage: shot_audit.py BEAT_DIR STORY.txt
For every shot (camera cut) in clips/clip1..5.mp4: a thumbnail of who is on screen, the words spoken during
that shot (Palmier's word timings) tagged with the speaker the script expects, e.g.  "honestly[A] no[B]".
Writes BEAT_DIR/audit/shotNN.jpg, BEAT_DIR/audit.txt and BEAT_DIR/audit_sheet.jpg (all thumbnails, in order).
Look at each thumbnail next to its words: if the face on screen is not the expected speaker, that span is a mix-up.
Fix: a {"kind":"cut"} cover in covers.json when the fragment is redundant; otherwise re-generate that clip."""
import difflib
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pal import close_open_projects, j, session  # noqa: E402
from story import norm_words, parse  # noqa: E402

if len(sys.argv) != 3:
    sys.exit(__doc__)
B, story = os.path.abspath(sys.argv[1]), sys.argv[2]
script = parse(story)
os.makedirs(f"{B}/audit", exist_ok=True)

session(new=True)
close_open_projects()
j("manage_project", {"action": "create", "name": f"audit {os.path.basename(B)} {os.getpid()}", "fps": 30,
                     "aspectRatio": "9:16", "quality": "720p"})
lines_out, thumbs, n = [], [], 0
for k in range(1, 6):
    clip = f"{B}/clips/clip{k}.mp4"
    ref = j("import_media", {"source": {"path": clip}})["mediaRef"]
    j("add_clips", {"entries": [{"mediaRef": ref, "startFrame": 0}]})
    words = [(w, f / 30) for c in j("get_transcript", {})["clips"] for _, w, f in c["words"]]
    j("remove_clips", {"clipIds": [c["id"] for t in j("get_timeline", {})["tracks"] for c in t.get("clips", [])]})
    exp = [(w, who) for who, t in script[k - 1] for w in norm_words(t)]
    got = [(norm_words(w) or [""])[0] for w, _ in words]
    sm = difflib.SequenceMatcher(a=got, b=[w for w, _ in exp], autojunk=False)
    who_for = [None] * len(got)
    for a0, b0, size in sm.get_matching_blocks():
        for i in range(size):
            who_for[a0 + i] = exp[b0 + i][1]
    for i in range(len(who_for)):  # fill gaps from neighbours
        if who_for[i] is None:
            who_for[i] = next((who_for[x] for x in range(i - 1, -1, -1) if who_for[x]), None) or next((e for e in who_for[i:] if e), "?")
    out = subprocess.run(["ffmpeg", "-i", clip, "-vf", "select='gt(scene,0.25)',showinfo", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    L = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", clip],
                             capture_output=True, text=True).stdout.strip())
    cuts = [0.0] + [float(x) for x in re.findall(r"pts_time:([\d.]+)", out)] + [L]
    for s, e in zip(cuts, cuts[1:]):
        if e - s < 0.15:
            continue
        n += 1
        thumb = f"{B}/audit/shot{n:02d}.jpg"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{(s + e) / 2:.2f}", "-i", clip, "-frames:v", "1", "-vf", "scale=180:-1", thumb])
        thumbs.append(thumb)
        ws = " ".join(f"{w}[{x}]" for (w, t), x in zip(words, who_for) if s <= t < e)
        lines_out.append(f"shot{n:02d}  clip{k} {s:5.2f}-{e:5.2f}s  {ws}")
j("manage_project", {"action": "close"})
open(f"{B}/audit.txt", "w").write("\n".join(lines_out) + "\n")
lst = f"{B}/audit/list.txt"
open(lst, "w").write("".join(f"file '{t}'\n" for t in thumbs))
cols = 8
rows = (len(thumbs) + cols - 1) // cols
subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-vf", f"tile={cols}x{rows}", "-frames:v", "1",
                f"{B}/audit_sheet.jpg"])
print("\n".join(lines_out))
print(f"\n{n} shots. Thumbnails in order: {B}/audit_sheet.jpg (8 per row) and {B}/audit/shotNN.jpg")
