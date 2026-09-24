#!/usr/bin/env python3
"""Fix caption text in a beat's saved Palmier project, then re-export 9:16, 3:4 and the project.
Captions come from speech recognition, which mishears brand names (a brand word heard as a common word),
drops the $ on prices and captions grunts ("M", "Uh"). This fixes them and refuses to export if any remain.

usage: fix_caps.py BEAT_DIR [BEAT_DIR...] --brand "Brand Name" [--fix WRONG=RIGHT ...] [--price 180 ...] [--dry-run]
  --brand   the brand as it must be spelled; the full name and its first word get their capitals back ("optimate" -> "Optimate")
  --fix     a mishearing to replace, whole word, any case (repeatable), e.g. --fix Otimate=Optimate
  --price   a number that is a price in this ad, so a bare "180" becomes "$180" (repeatable)
  --dry-run print the changes, don't touch the project
Reads BEAT_DIR/project.palmier; writes final_9x16.mp4, final_3x4.mp4, project.palmier (and uses edit_log.json crop windows)."""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pal import PalmierError, close_open_projects, j, session, wait_export  # noqa: E402
from edit_beat import crop34  # noqa: E402

FILLER = {"m", "mm", "uh", "um", "ah", "er", "erm", "eh", "oh", "hm", "hmm", "huh", "mhm"}


def build_rules(brand, fixes, prices):
    rules = []
    for f in fixes:
        wrong, right = f.split("=", 1)
        rules.append((rf"\b{re.escape(wrong)}\b", right, re.I))
    if brand:
        # the full name, and its first word alone (captions split "Go to optimate | savings and see")
        rules.append((rf"\b{re.escape(brand)}\b", brand, re.I))
        first = brand.split()[0]
        rules.append((rf"\b{re.escape(first)}\b", first, re.I))
    for p in prices:
        rules.append((rf"(?<![\$\d])\b{re.escape(p)}\b", f"${p}", 0))
    return rules


def fixer(rules):
    def fix(text):
        words = text.split()
        while len(words) > 1 and words[0].lower().strip(".,?!—-…") in FILLER:
            words = words[1:]  # leading grunt glued to a real word ("M Here are")
        out = " ".join(words)
        for pat, rep, flags in rules:
            out = re.sub(pat, rep, out, flags=flags)
        return out
    return fix


def captions():
    return [c for t in j("get_timeline", {"captionDetail": True})["tracks"] for g in t.get("captionGroups", []) for c in g["clips"]]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("beat_dirs", nargs="+")
    ap.add_argument("--brand", required=True)
    ap.add_argument("--fix", action="append", default=[])
    ap.add_argument("--price", action="append", default=[])
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    fix = fixer(build_rules(a.brand, a.fix, a.price))
    wrong_words = [f.split("=", 1)[0] for f in a.fix]
    session(new=True)
    for d in a.beat_dirs:
        B = os.path.abspath(os.path.expanduser(d))
        name = os.path.basename(B)
        close_open_projects()
        j("manage_project", {"action": "open", "path": f"{B}/project.palmier"})
        caps = captions()
        drop = [c[0] for c in caps if all(w.lower().strip(".,?!—-…") in FILLER for w in c[3].split())]
        if drop:
            print(name, "remove filler captions:", [c[3] for c in caps if c[0] in drop])
            if not a.dry_run:
                j("remove_clips", {"clipIds": drop})
        for cid, s, e, text in [c for c in caps if c[0] not in drop]:
            new = fix(text)
            if new != text:
                print(name, f"{text!r} -> {new!r}")
                if not a.dry_run:
                    j("update_text", {"clipIds": [cid], "content": new})
        if a.dry_run:
            continue
        after = sorted(captions(), key=lambda c: c[1])
        bad = [c[3] for c in after if fix(c[3]) != c[3] or any(re.search(rf"\b{re.escape(w)}\b", c[3], re.I) for w in wrong_words)]
        if bad:
            sys.exit(f"{name}: captions still wrong, not exporting: {bad}")
        out916 = f"{B}/final_9x16.mp4"
        wait_export(j("export_project", {"mode": "video", "codec": "H.264", "resolution": "1080p", "outputPath": out916})["jobId"])
        windows = []
        if os.path.exists(f"{B}/edit_log.json"):
            windows = [tuple(w) for w in json.load(open(f"{B}/edit_log.json")).get("crop_windows", [])]
        crop34(out916, f"{B}/final_3x4.mp4", windows)
        j("export_project", {"mode": "palmier", "outputPath": f"{B}/project.palmier"})
        print(name, "exported. captions:", " | ".join(c[3] for c in after), flush=True)


if __name__ == "__main__":
    try:
        main()
    except PalmierError as e:
        sys.exit(f"Palmier: {e}\nIf it timed out, run it again.")
