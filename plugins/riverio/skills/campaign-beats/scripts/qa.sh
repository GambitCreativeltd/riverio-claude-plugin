#!/bin/bash
export PATH="$PATH:/opt/homebrew/bin:/usr/local/bin"
# Technical QA of finished beats. usage: qa.sh BEAT_DIR [BEAT_DIR...]
# Per beat: length, loudness (target -16 LUFS), black flashes, sizes of both finals,
# and BEAT_DIR/qa_sheet.jpg (one frame per second) to LOOK at for burned-in text, name labels, logos, glitches.
# Exit code 1 if anything is off.
fail=0
for B in "$@"; do
  B="${B%/}"; n=$(basename "$B"); f="$B/final_9x16.mp4"; f34="$B/final_3x4.mp4"
  if [ ! -f "$f" ]; then echo "$n: MISSING $f"; fail=1; continue; fi
  d=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$f")
  L=$(ffmpeg -nostats -i "$f" -af ebur128 -f null - 2>&1 | grep -E "^\s+I:" | tail -1 | awk '{print $2}')
  bl=$(ffmpeg -i "$f" -vf blackdetect=d=0.03:pix_th=0.05 -an -f null - 2>&1 | grep -c black_start)
  s916=$(ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=p=0 "$f")
  s34=$( [ -f "$f34" ] && ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=p=0 "$f34" || echo missing)
  ffmpeg -v error -y -i "$f" -vf "fps=1,scale=180:-1,tile=8x8" -frames:v 1 "$B/qa_sheet.jpg"
  notes=""
  awk -v l="$L" 'BEGIN{exit !(l < -17.5 || l > -14.5)}' && notes="$notes loudness-off"
  [ "$bl" != "0" ] && notes="$notes black-frames"
  [ "$s916" != "1080,1920" ] && notes="$notes 9x16-size"
  [ "$s34" != "1080,1440" ] && notes="$notes 3x4-size"
  [ -n "$notes" ] && fail=1
  printf '%s  len=%.1fs  loud=%sLUFS  black=%s  9:16=%s  3:4=%s  %s\n' "$n" "$d" "$L" "$bl" "$s916" "$s34" "${notes:-OK}"
  echo "   look at: $B/qa_sheet.jpg"
done
exit $fail
