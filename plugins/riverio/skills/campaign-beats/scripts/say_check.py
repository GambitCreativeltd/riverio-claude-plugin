#!/usr/bin/env python3
"""After the edit: what each clip ACTUALLY says (Palmier's transcript, saved by edit_beat.py) vs the story.
Catches dropped/garbled lines, and checks the call to action says the brand IN FULL.
usage: say_check.py BEAT_DIR STORY.txt --brand "Brand Name" [--number 180=hundred and eighty]
Exit code 1 if a line is under 80% or the last clip never says the full brand name."""
import argparse, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from story import coverage, norm_words, parse

ap = argparse.ArgumentParser()
ap.add_argument("beat_dir"); ap.add_argument("story"); ap.add_argument("--brand", required=True)
ap.add_argument("--number", action="append", default=[], help="optional: how a written token is spoken, e.g. 24/7=twenty four seven")
a = ap.parse_args()
spans = json.load(open(os.path.join(a.beat_dir, "edit_log.json")))["spans"]
said = [s[2] for s in spans]


def spoken(t):
    for n in a.number:
        k, v = n.split("=", 1)
        t = t.replace(k, v)
    return t


bad = 0
for k, lines in enumerate(parse(a.story), 1):
    for who, text in lines:
        r = coverage(spoken(text), spoken(said[k - 1]))
        if r < 0.8:
            bad += 1
            print(f"clip{k} {r:.0%} {who}: {text!r}\n        heard: {said[k - 1]!r}")
brand = " ".join(norm_words(a.brand))
if brand not in " ".join(norm_words(said[-1])):
    bad += 1
    print(f"CTA: the last clip never says {a.brand!r} in full. Heard: {said[-1]!r}")
else:
    print(f"CTA says {a.brand!r} - now LISTEN to it: it must invite, not contradict (e.g. \"Don't settle for {a.brand}\" is wrong).")
print("say check ok" if not bad else f"{bad} problem(s)")
sys.exit(1 if bad else 0)
