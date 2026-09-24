#!/usr/bin/env python3
"""Build the brand segment that story beats put inside clip 4 (e.g. phone showing the product, mascot, price card).

Two ways:
  1) cut it out of the SOURCE beat's final (fastest; only if everything in its audio is licensed - no songs):
       brand_segment.py --out brand.mp4 --cut SOURCE_FINAL.mp4 29.167 38.9
  2) build it from parts (video only), then lay a voice-over and/or a licensed music bed under it:
       brand_segment.py --out brand.mp4 --part phone.mp4:0-9@3 --part mascot.mp4:4.633-7.2 --part price_card.png:2.5 \
                        [--vo vo.mp3] [--music bed.mp3 --music-db -20]
     --part FILE[:START-END][@SPEED]   a video piece (SPEED 3 = 3x faster);  FILE.png:SECONDS = a still for N seconds
Output: 1080x1920, 30 fps, H.264/AAC, audio at about -16 LUFS. Prints the length.
Never use a song or music you don't have a license for; a silent segment is better than an unlicensed one."""
import argparse
import os
import re
import subprocess
import sys
import tempfile
os.environ["PATH"] = os.environ.get("PATH", "") + ":/opt/homebrew/bin:/usr/local/bin"  # Homebrew ffmpeg when launched from the app


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"ffmpeg failed: {' '.join(cmd)}\n{r.stderr[-1500:]}")
    return r


def dur(p):
    return float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p]).stdout.strip())


FIT = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30,setsar=1,format=yuv420p"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True)
    ap.add_argument("--cut", nargs=3, metavar=("VIDEO", "START", "END"))
    ap.add_argument("--part", action="append", default=[])
    ap.add_argument("--vo")
    ap.add_argument("--music")
    ap.add_argument("--music-db", type=float, default=-20)
    a = ap.parse_args()
    out = os.path.abspath(os.path.expanduser(a.out))

    if a.cut:
        v, s, e = a.cut
        has_audio = bool(run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of", "csv=p=0", v]).stdout.strip())
        audio = ["-af", "loudnorm=I=-16:TP=-1.5:LRA=11"] if has_audio else ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-shortest"]
        run(["ffmpeg", "-v", "error", "-y", "-ss", s, "-to", e, "-i", v, *audio, "-vf", FIT,
             "-c:v", "libx264", "-crf", "16", "-preset", "slow", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", out])
        print(f"{out}: {dur(out):.2f}s (cut {s}-{e} from {os.path.basename(v)})")
        return
    if not a.part:
        sys.exit("give --cut or at least one --part")

    tmp = tempfile.mkdtemp(prefix="brandseg_")
    pieces = []
    for n, spec in enumerate(a.part):
        m = re.match(r"^(.+?)(?::([\d.]+)(?:-([\d.]+))?)?(?:@([\d.]+))?$", spec)
        f, s, e, speed = m.group(1), m.group(2), m.group(3), float(m.group(4) or 1)
        p = f"{tmp}/p{n}.mp4"
        if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
            secs = s or "2"
            run(["ffmpeg", "-v", "error", "-y", "-loop", "1", "-t", secs, "-i", f, "-vf", FIT, "-an", "-c:v", "libx264", "-crf", "16", p])
        else:
            cmd = ["ffmpeg", "-v", "error", "-y"]
            if s:
                cmd += ["-ss", s]
            if e:
                cmd += ["-to", e]
            cmd += ["-i", f, "-vf", f"setpts=PTS/{speed},{FIT}", "-an", "-c:v", "libx264", "-crf", "16", p]
            run(cmd)
        pieces.append(p)
    lst = f"{tmp}/list.txt"
    open(lst, "w").write("".join(f"file '{p}'\n" for p in pieces))
    video = f"{tmp}/video.mp4"
    run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", video])
    L = dur(video)

    ins, mix, n_in = ["-i", video], [], 1
    if a.vo:
        ins += ["-i", a.vo]
        mix.append(f"[{n_in}:a]apad,atrim=0:{L:.3f}[vo]"); n_in += 1
    if a.music:
        ins += ["-stream_loop", "-1", "-i", a.music]
        mix.append(f"[{n_in}:a]atrim=0:{L:.3f},volume={a.music_db}dB,afade=t=out:st={max(0, L - 0.4):.3f}:d=0.4[mu]"); n_in += 1
    labels = ("[vo]" if a.vo else "") + ("[mu]" if a.music else "")
    if not labels:
        # silent segment: add a silent track so every clip in the edit has audio
        run(["ffmpeg", "-v", "error", "-y", "-i", video, "-f", "lavfi", "-t", f"{L:.3f}", "-i", "anullsrc=r=48000:cl=stereo",
             "-c:v", "copy", "-c:a", "aac", "-shortest", out])
    else:
        n = labels.count("[")
        graph = ";".join(mix) + f";{labels}amix=inputs={n}:normalize=0,loudnorm=I=-16:TP=-1.5:LRA=11[a]"
        run(["ffmpeg", "-v", "error", "-y", *ins, "-filter_complex", graph, "-map", "0:v", "-map", "[a]",
             "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-t", f"{L:.3f}", out])
    print(f"{out}: {L:.2f}s from {len(pieces)} part(s)" + (" + VO" if a.vo else "") + (" + music" if a.music else ""))


if __name__ == "__main__":
    main()
