"""Read a beat's story/script into 5 clips of spoken lines. Shared by say_check.py and dialogue_check.py.
Understands both source formats:
  story   : "BEAT 1: ..." headings, lines like  DAD: Twenty years...   /  HER (quiet): (looks up) Says who?
  podcast : "CLIP 1 OF 5" headings, lines like    A [0.0-3.2] "Line text" (delivery)"""
import os
import re
os.environ["PATH"] = os.environ.get("PATH", "") + ":/opt/homebrew/bin:/usr/local/bin"  # Homebrew ffmpeg when launched from the app

norm_words = lambda s: re.sub(r"[^a-z0-9 ]", " ", s.lower().replace("’", "'").replace("'", "")).split()


def parse(path):
    txt = open(path).read()
    clips = []
    if re.search(r"^CLIP \d OF \d", txt, re.M):
        for block in [b for b in re.split(r"\n(?=CLIP \d OF \d)", "\n" + txt) if re.match(r"CLIP \d OF", b)][:5]:
            lines = re.findall(r"^\s*([A-Z])\s*\[[^\]]*\]\s+\"(.+?)\"", block, re.M)
            clips.append([(who, t) for who, t in lines])
    else:
        parts = re.split(r"\n\s*BEAT (\d)\s*:", "\n" + txt)
        for i in range(1, len(parts) - 1, 2):
            body = parts[i + 1]
            lines = re.findall(r"^([A-Z][A-Z .'’]+?)(?: \([^)]*\))?: (?:\([^)]*\) )?(.+)$", body, re.M)
            clips.append([(who.strip(), t.strip()) for who, t in lines if who.strip() not in ("NOTES",)])
        clips = clips[:5]
    if len(clips) != 5:
        raise SystemExit(f"{path}: found {len(clips)} clips, expected 5 (BEAT 1..5 or CLIP 1 OF 5 .. CLIP 5 OF 5)")
    return clips


UNITS = {w: i for i, w in enumerate("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen "
                                     "fifteen sixteen seventeen eighteen nineteen".split())}
TENS = {w: 10 * i for i, w in enumerate("_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()) if w != "_"}


def canon(words):
    """spoken numbers -> digits, so "a hundred and eighty" == "180" and "twenty" == "20"."""
    out, i = [], 0
    while i < len(words):
        n, j, seen = 0, i, False
        cur = 0
        while j < len(words):
            w = words[j]
            if w in UNITS: cur += UNITS[w]
            elif w in TENS: cur += TENS[w]
            elif w == "hundred": cur = max(cur, 1) * 100
            elif w == "thousand": n += max(cur, 1) * 1000; cur = 0
            elif w == "a" and j + 1 < len(words) and words[j + 1] in ("hundred", "thousand"): pass
            elif w == "and" and seen and j + 1 < len(words) and (words[j + 1] in UNITS or words[j + 1] in TENS): pass
            else: break
            seen = True; j += 1
        if seen and j > i and not (j == i + 1 and words[i] == "a"):
            out.append(str(n + cur)); i = j
        else:
            out.append(words[i]); i += 1
    return [w[:-1] if len(w) > 3 and w.endswith("s") else w for w in out]  # plurals/possessives match


def coverage(line, text):
    """share of the line's words heard, in order, inside text (0..1)"""
    import difflib
    w, t = canon(norm_words(line)), canon(norm_words(text))
    if not w:
        return 1.0
    sm = difflib.SequenceMatcher(None, w, t, autojunk=False)
    return sum(b.size for b in sm.get_matching_blocks()) / len(w)
