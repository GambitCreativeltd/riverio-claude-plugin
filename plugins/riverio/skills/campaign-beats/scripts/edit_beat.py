#!/usr/bin/env python3
"""Assemble one beat in Palmier Pro from its 5 generated clips, then export 9:16 + 3:4 + the Palmier project.

usage:
  edit_beat.py BEAT_DIR --style podcast|story --endcard END.mp4 [options]

BEAT_DIR must hold clips/clip1.mp4 .. clips/clip5.mp4 (the canvas's 5 videos, in story order).
Writes BEAT_DIR/final_9x16.mp4, final_3x4.mp4, project.palmier, edit_log.json.

styles (pick the one the SOURCE beat used):
  podcast  two people talking. Each clip trimmed tight to its speech. Optional b-roll on keywords (--broll).
  story    cartoon / acted scene. Keep the action around the lines. Optional brand segment inside clip 4
           (--brand-segment) and an overlay image when a word is first said (--overlay/--overlay-words).

options:
  --title T               project name in Palmier (default: folder name)
  --endcard FILE          end card video, placed last
  --endcard-seconds S     how much of the end card to use (default: podcast 4.9, story 2.0)
  --endcard-mute          mute the end card audio (generated end-card audio is often garbled speech)
  --brand-segment FILE    story: a ready brand segment (its own VO/captions/music - licensed only) put inside clip 4
  --overlay PNG           story: image shown ~2.5s when one of --overlay-words is first said (e.g. a neon price)
  --overlay-words a,b     words that trigger the overlay (default: none)
  --broll FILE.json       podcast: b-roll plan, list of
                          {"words":["questions"],"file":"/path/broll.mp4","from":0.5,"to":3.0,
                           "zoom":1.5,"cx":0.53,"cy":0.42,"crop34_y":60}
                          first time any word is said -> that b-roll (video only) goes on top, 3 frames early.
                          crop34_y: where the 3:4 crop starts (px from top of 1920) while it shows (default 240 = center)
  --covers FILE.json      per-clip fixes, times are SOURCE seconds inside that clip:
                          {"clip":2,"kind":"start","from":1.2}      start later/earlier
                          {"clip":2,"kind":"end","to":8.4}          end earlier/later
                          {"clip":3,"kind":"cut","from":4.1,"to":5.0}   remove a bad fragment (voice mix-up, filler)
                          {"clip":1,"kind":"zoom","scale":1.5,"cy":0.42}            zoom the whole clip
                          {"clip":1,"kind":"zoom","from":2,"to":4,"scale":1.35,"cy":0.62}  zoom only a span
                            centerY = where the clip's CENTER sits: LOWER cy (0.42) pushes the TOP off-frame
                            (hides burned-in name labels at the top); HIGHER cy (0.62) hides the bottom (subtitles).
                          {"clip":5,"kind":"broll","from":2.6,"to":5.9,"file":"/path/broll.mp4","src":16.5}  podcast
                          {"clip":4,"kind":"pre","from":0,"to":1.6} / {"clip":4,"kind":"post","from":6,"to":10}
                            story: the pieces of clip 4 before / after the brand segment
  --caption-y Y           caption height 0..1 (default podcast 0.62, story 0.77)
  --caption-size N        caption font size (default podcast 78, story 70)
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pal import PalmierError, close_open_projects, j, session, wait_export  # noqa: E402

FPS = 30
FILLER = {"uh", "um", "hm", "hmm", "mm", "mhm", "uhh", "umm", "huh"}


def dur(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                         capture_output=True, text=True).stdout.strip()
    return float(out or 0)


def lufs(path, s0=None, s1=None):
    cmd = ["ffmpeg", "-nostats"]
    if s0 is not None:
        cmd += ["-ss", str(s0), "-t", str(max(0.1, s1 - s0))]
    cmd += ["-i", path, "-af", "ebur128", "-f", "null", "-"]
    out = subprocess.run(cmd, capture_output=True, text=True).stderr
    hits = re.findall(r"I:\s+(-?[\d.]+) LUFS", out)
    return float(hits[-1]) if hits else -16.0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("beat_dir")
    ap.add_argument("--style", choices=("podcast", "story"), required=True)
    ap.add_argument("--title")
    ap.add_argument("--endcard", required=True)
    ap.add_argument("--endcard-seconds", type=float)
    ap.add_argument("--endcard-mute", action="store_true")
    ap.add_argument("--brand-segment")
    ap.add_argument("--overlay")
    ap.add_argument("--overlay-words", default="")
    ap.add_argument("--broll")
    ap.add_argument("--covers")
    ap.add_argument("--caption-y", type=float)
    ap.add_argument("--caption-size", type=int)
    a = ap.parse_args()

    podcast = a.style == "podcast"
    B = os.path.abspath(os.path.expanduser(a.beat_dir))
    clip_path = {i: f"{B}/clips/clip{i}.mp4" for i in range(1, 6)}
    for i, p in clip_path.items():
        if not os.path.exists(p):
            sys.exit(f"missing {p} - download the 5 canvas videos into {B}/clips/ first")
    covers = json.load(open(a.covers)) if a.covers else []
    broll_plan = json.load(open(a.broll)) if a.broll else []
    end_s = a.endcard_seconds or (4.9 if podcast else 2.0)
    cap_y = a.caption_y or (0.62 if podcast else 0.77)
    cap_size = a.caption_size or (78 if podcast else 70)
    title = a.title or os.path.basename(B)
    CAP = {"maxWords": 3, "animation": "highlightPop", "highlightColor": "#FFE600",
           "style": {"fontName": "Avenir Next Heavy", "fontCase": "uppercase", "bold": True, "color": "#FFFFFF",
                     "fontSize": cap_size, "alignment": "center", "outline": {"enabled": True, "color": "#000000", "width": 6},
                     "shadow": {"enabled": True, "color": "#000000", "opacity": 0.5, "blur": 8, "offset": {"x": 0, "y": 3}}},
           "transform": {"x": 0.5, "y": cap_y}}

    def cv(i, kind):
        return [c for c in covers if c.get("clip") == i and c["kind"] == kind]

    session(new=True)
    close_open_projects()
    j("manage_project", {"action": "create", "name": f"{title} {time.strftime('%H%M%S')}", "fps": FPS,
                         "aspectRatio": "9:16", "quality": "1080p"})
    ref = {f"clip{i}": j("import_media", {"source": {"path": clip_path[i]}, "folder": "Clips"})["mediaRef"] for i in range(1, 6)}
    ref["end"] = j("import_media", {"source": {"path": os.path.abspath(a.endcard)}, "folder": "Brand"})["mediaRef"]
    if a.brand_segment:
        ref["brand"] = j("import_media", {"source": {"path": os.path.abspath(a.brand_segment)}, "folder": "Brand"})["mediaRef"]
    if a.overlay:
        ref["overlay"] = j("import_media", {"source": {"path": os.path.abspath(a.overlay)}, "folder": "Brand"})["mediaRef"]
    for k, bp in enumerate(broll_plan):
        ref[f"broll{k}"] = j("import_media", {"source": {"path": os.path.abspath(bp["file"])}, "folder": "B-roll"})["mediaRef"]
    for k, c in enumerate([c for c in covers if c["kind"] == "broll" and c.get("file")]):
        c["_ref"] = j("import_media", {"source": {"path": os.path.abspath(c["file"])}, "folder": "B-roll"})["mediaRef"]

    def speech(i):
        # Palmier transcribes on import; it may not be ready yet. A silent clip never gets segments.
        for _ in range(40 if podcast else 20):
            m = j("inspect_media", {"mediaRef": ref[f"clip{i}"]})
            if isinstance(m, dict) and m.get("transcription", {}).get("segments"):
                return m["transcription"]["segments"]
            time.sleep(3)
        return []

    # 1. spans per clip: podcast = tight to the words; story = keep the action around the lines
    spans, pieces_of = [], {}
    for i in range(1, 6):
        L = dur(clip_path[i])
        segs = speech(i)
        if podcast:
            s0 = max(0.0, segs[0][1] - 0.15) if segs else 0.0
            s1 = min(L, segs[-1][2] + 0.35) if segs else L
        else:
            s0 = max(0.0, segs[0][1] - 2.0) if segs else 0.0
            s1 = min(L, segs[-1][2] + 1.0) if segs else L
        for c in cv(i, "start"):
            s0 = c["from"]
        for c in cv(i, "end"):
            s1 = c["to"]
        spans.append((s0, s1, " ".join(s[0] for s in segs)))
        pieces = [(s0, s1)]
        for c in cv(i, "cut"):
            nxt = []
            for x, y in pieces:
                if c["to"] <= x or c["from"] >= y:
                    nxt.append((x, y))
                else:
                    if c["from"] > x:
                        nxt.append((x, c["from"]))
                    if c["to"] < y:
                        nxt.append((c["to"], y))
            pieces = nxt
        pieces_of[i] = pieces

    # story: clip 4 wraps the brand segment (short lead-in before it, the line/reaction after it)
    brand_len = 0
    if a.brand_segment:
        brand_len = dur(a.brand_segment)
        segs4 = speech(4)
        L4 = dur(clip_path[4])
        pre = cv(4, "pre")[0] if cv(4, "pre") else {"from": 0.0, "to": 1.6}
        if cv(4, "post"):
            post = cv(4, "post")[0]
        elif segs4:
            post = {"from": max(0.0, segs4[0][1] - 0.6), "to": L4}
        else:
            post = {"from": max(0.0, L4 - 2.8), "to": L4}
        pieces_of[4] = [(pre["from"], pre["to"]), "BRAND", (post["from"], post["to"])]

    entries, frame = [], 0
    for i in range(1, 6):
        for p in pieces_of[i]:
            if p == "BRAND":
                entries.append({"mediaRef": ref["brand"], "startFrame": frame, "source": [0, round(brand_len, 3)]})
                frame += round(brand_len * FPS)
                continue
            x, y = p
            entries.append({"mediaRef": ref[f"clip{i}"], "startFrame": frame, "source": [round(x, 3), round(y, 3)]})
            frame += round((y - x) * FPS)
    entries.append({"mediaRef": ref["end"], "startFrame": frame, "source": [0, end_s]})
    clips = j("add_clips", {"entries": entries})["clips"]
    j("set_project_settings", {"width": 1080, "height": 1920})

    # close 1-frame gaps left by 24->30 fps rounding (they render as black flashes)
    v_track = [t for t in j("get_timeline", {})["tracks"] if any(c["id"] == clips[0]["id"] for c in t.get("clips", []))][0]
    cur = {c["id"]: c["frames"] for c in v_track["clips"]}
    expected = 0
    for c in clips:
        s, e = cur[c["id"]]
        if s != expected:
            j("move_clips", {"moves": [{"clipId": c["id"], "toFrame": expected}]})
        c["frames"] = [expected, expected + (e - s)]
        expected += e - s
    key_of = [[k for k in ref if ref[k] == e["mediaRef"]][0] for e in entries]
    end_start = clips[-1]["frames"][0]
    brand_win = tuple(clips[key_of.index("brand")]["frames"]) if "brand" in key_of else None
    clip_start = {i: next(c["frames"][0] for c, k in zip(clips, key_of) if k == f"clip{i}") for i in range(1, 6)}

    def tl_frame(i, src_s):
        """timeline frame of a source second inside clip i (first piece)"""
        return clip_start[i] + round((src_s - pieces_of[i][0][0]) * FPS)

    # 2. loudness: every clip to ~-16 LUFS; end card lifted a little (or muted)
    gains = {}
    for i, (s0, s1, _) in enumerate(spans, 1):
        L = lufs(clip_path[i], s0, s1) if podcast else lufs(clip_path[i])
        gains[f"clip{i}"] = round(max(-10, min(12, -16 - L)), 1)
    for c, k in zip(clips, key_of):
        if not c.get("audio"):
            continue
        if k.startswith("clip"):
            j("set_clip_properties", {"clipIds": [c["audio"]["id"]], "volumeDb": gains[k], "fadeInFrames": 1, "fadeOutFrames": 1})
        elif k == "brand":
            j("set_clip_properties", {"clipIds": [c["audio"]["id"]], "volumeDb": 0, "fadeInFrames": 2, "fadeOutFrames": 2})
        elif k == "end":
            j("set_clip_properties", {"clipIds": [c["audio"]["id"]], "volumeDb": -60 if a.endcard_mute else 1, "fadeOutFrames": 10})

    words = [w for c in j("get_transcript", {})["clips"] for w in c["words"]]  # [idx, word, frame]
    norm = lambda w: re.sub(r"[^a-z0-9]", "", w.lower())

    # 3a. podcast b-roll on keywords (first hit each), never overlapping, never over the end card
    plan, crop_windows = [], []
    for k, bp in enumerate(broll_plan):
        want = {norm(w) for w in bp["words"]}
        hit = next((f for _, w, f in words if norm(w) in want and f < end_start), None)
        if hit is not None:
            plan.append((hit - 3, f"broll{k}", [bp.get("from", 0), bp.get("to", 2.5)], bp))
    for c in [c for c in covers if c["kind"] == "broll"]:
        s, e = tl_frame(c["clip"], c["from"]), tl_frame(c["clip"], c["to"])
        key = None
        if c.get("_ref"):
            ref[f"cover{id(c)}"] = c["_ref"]; key = f"cover{id(c)}"
        elif broll_plan:
            key = "broll0"
        if key:
            src0 = c.get("src", 0.0)
            plan.append((s, key, [src0, src0 + (e - s) / FPS], c))
    plan.sort(key=lambda x: x[0])
    used, b_entries, b_meta = [], [], []
    for st, key, src, meta in plan:
        ln = round((src[1] - src[0]) * FPS)
        if any(not (st + ln <= x or st >= y) for x, y in used) or st + ln > end_start:
            continue
        used.append((st, st + ln))
        b_entries.append({"mediaRef": ref[key], "startFrame": max(0, st), "source": src, "includeAudio": False})
        b_meta.append(meta)
    if b_entries:
        br = j("add_clips", {"entries": b_entries})["clips"]
        for c, meta in zip(br, b_meta):
            if meta.get("zoom"):
                z = meta["zoom"]
                j("set_clip_properties", {"clipIds": [c["id"]], "transform": {"width": z, "height": z,
                                           "centerX": meta.get("cx", 0.5), "centerY": meta.get("cy", 0.5)}})
            if meta.get("crop34_y") is not None:
                crop_windows.append((c["frames"][0] / FPS, c["frames"][1] / FPS, int(meta["crop34_y"])))

    # 3b. zoom covers (hide burned-in labels/subtitles): whole clip, or only a span
    for z in [c for c in covers if c["kind"] == "zoom"]:
        i = z["clip"]
        sc = z.get("scale", 1.35)
        tf = {"width": sc, "height": sc, "centerX": z.get("cx", 0.5), "centerY": z.get("cy", 0.5)}
        v1 = [t for t in j("get_timeline", {})["tracks"] if t["type"] == "video"
              and any(c["id"] == clips[0]["id"] for c in t.get("clips", []))][0]
        wins = [tuple(c["frames"]) for c, k in zip(clips, key_of) if k == f"clip{i}"]
        if "from" in z:
            s, e = tl_frame(i, z["from"]), tl_frame(i, z["to"])
            lo, hi = wins[0][0], wins[-1][1]
            pts = [p for p in (s, e) if lo < p < hi]
            if pts:
                j("split_clips", {"trackIndex": v1["index"], "frames": pts})
            v1 = [t for t in j("get_timeline", {})["tracks"] if t["trackId"] == v1["trackId"]][0]
            live = [c for c in v1["clips"] if max(s, lo) <= c["frames"][0] < min(e, hi)]
        else:
            live = [c for c in v1["clips"] if tuple(c["frames"]) in wins]
        if live:
            j("set_clip_properties", {"clipIds": [c["id"] for c in live], "transform": tf})
        print(f"zoom clip{i}: {len(live)} piece(s) scale {sc} cy {tf['centerY']}", flush=True)

    # 3c. story overlay (e.g. neon price) the first time a trigger word is said, before the brand segment
    overlay_at = None
    if a.overlay and a.overlay_words:
        want = {norm(w) for w in a.overlay_words.split(",")}
        limit = brand_win[0] if brand_win else end_start
        overlay_at = next((f for _, w, f in words if norm(w) in want and f < limit), None)
        if overlay_at is not None:
            st = max(0, overlay_at - 6)
            j("add_clips", {"entries": [{"mediaRef": ref["overlay"], "startFrame": st, "endFrame": st + 75}]})

    # 4. captions over all speech, then fill any gaps, drop filler-only captions, keep captions on top
    def caption(x, y):
        if y - x > 6:
            try:
                j("add_captions", {**CAP, "startFrame": x, "endFrame": y})
            except PalmierError as e:
                if "No speech" not in str(e):
                    raise  # a fill window over a lone breath/grunt is fine to skip
    caption(0, end_start)
    for attempt in range(3):
        capc = [c for t in j("get_timeline", {"captionDetail": True})["tracks"] for g in t.get("captionGroups", []) for c in g["clips"]]
        spoken = [f for c in j("get_transcript", {})["clips"] for _, w, f in c["words"] if f < end_start]
        miss = [f for f in spoken if not any(s <= f < e for _, s, e, _ in capc)]
        if len(miss) < 2:
            break
        runs, cur_r = [], [miss[0]]
        for f in miss[1:]:
            if f - cur_r[-1] > 45:
                runs.append(cur_r); cur_r = [f]
            else:
                cur_r.append(f)
        runs.append(cur_r)
        for r in runs:
            caption(max(0, r[0] - 3), min(end_start, r[-1] + 20))
        print(f"caption fill pass {attempt + 1}: {len(miss)} uncovered words", flush=True)
    capc = [c for t in j("get_timeline", {"captionDetail": True})["tracks"] for g in t.get("captionGroups", []) for c in g["clips"]]
    drop = [c[0] for c in capc if all(w.lower().strip(".,?!—-…") in FILLER for w in c[3].split())]
    if drop:
        j("remove_clips", {"clipIds": drop})
    for t in [t for t in j("get_timeline", {})["tracks"] if t.get("captionGroups")]:
        j("manage_tracks", {"reorder": [{"trackId": t["trackId"], "to": 0}]})

    # 5. exports: 9:16 from Palmier, 3:4 = crop 1080x1440 (center, or higher while a crop34_y b-roll shows)
    out916 = f"{B}/final_9x16.mp4"
    wait_export(j("export_project", {"mode": "video", "codec": "H.264", "resolution": "1080p", "outputPath": out916})["jobId"])
    crop34(out916, f"{B}/final_3x4.mp4", crop_windows)
    j("export_project", {"mode": "palmier", "outputPath": f"{B}/project.palmier"})
    json.dump({"style": a.style, "spans": spans, "pieces": {k: [p if p == "BRAND" else list(p) for p in v] for k, v in pieces_of.items()},
               "clip_start": clip_start, "end_start": end_start, "brand_win": brand_win, "overlay_frame": overlay_at,
               "broll": [(e["startFrame"] / FPS, e["source"]) for e in b_entries], "crop_windows": crop_windows, "covers": covers},
              open(f"{B}/edit_log.json", "w"), indent=1, default=str)
    print(json.dumps({"beat": os.path.basename(B), "length_s": round((end_start + end_s * FPS) / FPS, 2),
                      "final_9x16": out916, "final_3x4": f"{B}/final_3x4.mp4", "project": f"{B}/project.palmier"}, indent=1))


def crop34(src, dst, windows=()):
    expr = "240"
    for x, y, top in windows:
        expr = f"if(between(t,{x:.2f},{y:.2f}),{top},{expr})"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-vf", f"crop=1080:1440:0:'{expr}'", "-c:v", "libx264",
                    "-crf", "16", "-preset", "slow", "-c:a", "copy", dst], check=True)


if __name__ == "__main__":
    try:
        main()
    except PalmierError as e:
        sys.exit(f"Palmier: {e}\nIf a step timed out (closing projects, transcription not ready), just run it again.")
