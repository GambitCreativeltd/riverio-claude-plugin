#!/usr/bin/env python3
"""Before videos: is every story line inside its clip prompt? (The clip-prompt agent sometimes drops or rewrites lines.)
usage: dialogue_check.py STORY.txt PROMPTS
  PROMPTS = the get_outputs JSON saved to a file (uses its "clipPrompts"), or a folder with clip1.txt..clip5.txt
Prints every missing line; exit code 1 if any are missing."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from story import coverage, parse

if len(sys.argv) != 3:
    sys.exit(__doc__)
story, src = sys.argv[1], sys.argv[2]
if os.path.isdir(src):
    import glob
    prompts = []
    for k in range(1, 6):
        hits = sorted(glob.glob(os.path.join(src, f"*clip{k}.txt")))
        if not hits:
            sys.exit(f"no clip{k}.txt in {src}")
        prompts.append(open(hits[0]).read())
else:
    d = json.load(open(src))
    prompts = d["clipPrompts"] if isinstance(d, dict) else d
if len(prompts) != 5:
    sys.exit(f"expected 5 clip prompts, got {len(prompts)}")
missing = 0
for k, (lines, prompt) in enumerate(zip(parse(story), prompts), 1):
    for who, text in lines:
        if coverage(text, prompt) < 0.8:
            missing += 1
            print(f"clip{k} MISSING {who}: {text}")
print("all story lines are in the clip prompts" if not missing else f"{missing} line(s) missing")
sys.exit(1 if missing else 0)
