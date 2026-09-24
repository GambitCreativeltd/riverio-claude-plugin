# QA before showing anyone

Run for every beat, fix, re-export, run again. Only show finals that pass.

**Automatic**
- `qa.sh beats/beat6 beats/beat7 ...` - length, loudness (target **-16 LUFS**, OK -17.5..-14.5), **black frames = 0**,
  9:16 is 1080x1920 and **3:4 is 1080x1440**. It also writes `qa_sheet.jpg` (one frame per second).
- `say_check.py beats/beatN beats/beatN/story.txt --brand "<Brand Name>"` - what each clip actually says vs the
  story. Every line >= 80%, and **the CTA says the brand name in full**.
- `fix_caps.py ... --dry-run` - nothing left to change in the captions.

**With your eyes (open `qa_sheet.jpg`, and frames around anything suspicious)**
- **Dialogue vs story:** the right person says each line (podcast: `shot_audit.py`); no line said twice or by both.
- **The CTA invites** ("Go to <Brand Name> and see...") - never a line that sounds like avoid/settle-for the brand.
- **Captions spell the brand right** and show prices with "$"; no "UH"/"M" captions.
- **No burned-in text** from the video model: name labels, subtitles, fake logos, garbled words -> zoom (LOWER cy
  hides the top) or cut.
- **No unlicensed music** anywhere (brand segment included). Speech, licensed beds and sound effects only.
- **No black frames or flashes**, no frozen frames, no one-frame jumps between clips.
- **3:4 crop** keeps faces, captions and anything important (b-roll with key content near the top needs `crop34_y`).
- Same characters, same outfits, same place across all 5 clips; the end card is last and clean.

Then show the finals (paths for both ratios) and wait for an explicit "upload".
