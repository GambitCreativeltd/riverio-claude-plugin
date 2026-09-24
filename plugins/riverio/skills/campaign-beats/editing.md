# Editing in Palmier Pro

Palmier Pro must be open, with its MCP server turned on in its settings. `scripts/pal.py --ping` checks it.
You can drive Palmier with its MCP tools directly for small fixes (open the beat's `project.palmier`, change,
export). The scripts do the full assembly in one go.

## Brand pieces (once per campaign)
- **End card:** from `get_brand_assets`, or cut the last ~2-5 s of the SOURCE beat's final 9:16 with
  `ffmpeg -ss <start> -i source_final.mp4 -t <len> -c:v libx264 -crf 16 -c:a aac brand/endcard.mp4`.
  Generated end-card audio is often garbled speech -> `--endcard-mute`.
- **Brand segment (story style):** the product moment inside clip 4 (phone b-roll, mascot, price card).
  `scripts/brand_segment.py` either cuts it out of the source beat's final (`--cut`) - ONLY if its audio has no
  unlicensed music - or builds it from parts (`--part`) with an optional voice-over/licensed music bed.
  A song you can't prove is licensed = leave it out (a past segment had to be rebuilt for exactly this).
  If the source's price card has captions or music burned in, redraw it: `scripts/price_card.py --old 180 --new 100
  --out brand/price_card.mp4` (use the prices the source beat showed; a new saving is a claim - ask).
  Burned-in captions on other pieces: cut around them, or `ffmpeg -vf "delogo=x=..:y=..:w=..:h=..:enable='between(t,a,b)'"`
  only while the caption is on screen (it smears anything under it).
  **Voice-over for the segment:** reuse the campaign's existing segment voice if there is one; the tools here can't
  generate speech yet - if a new one is needed, tell them and ask Eliad for the voice file.
- **Interview style:** same as story style (brand segment inside clip 4, neon price, end card) - use `--style story`.
- **Overlay (story style):** e.g. a neon price PNG shown when the price is first said (`--overlay`, `--overlay-words`).

## Assemble a beat
(`$S` = this skill's `scripts/` folder, the one SKILL.md points to; run from the campaign folder)
```
python3.12 $S/edit_beat.py ~/Riverio/<campaign>/beats/beat6 --style story \
   --endcard brand/endcard.mp4 --brand-segment brand/brand_segment.mp4 \
   --overlay brand/price.png --overlay-words 180,eighty --covers beats/beat6/covers.json
python3.12 $S/edit_beat.py ~/Riverio/<campaign>/beats/beat6 --style podcast \
   --endcard brand/endcard.mp4 --endcard-mute --broll brand/broll.json
```
What it does: imports the 5 clips, trims each (podcast: tight to the words; story: keeps the action), closes
1-frame gaps (they flash black), brings speech to about -16 LUFS, places b-roll/brand segment/overlay, adds
captions (3 words, yellow highlight) over all speech and fills gaps, drops filler-only captions ("UH", "UM"),
exports `final_9x16.mp4`, crops `final_3x4.mp4` (1080x1440), saves `project.palmier` and `edit_log.json`.
Run `edit_beat.py --help` for every option.

## Fixing what you see (covers.json, then re-run edit_beat.py)
Times are seconds inside that clip's ORIGINAL file.
- **Burned-in labels/names at the top** ("HER", "GRANDMA"): `{"clip":2,"kind":"zoom","scale":1.5,"cy":0.42}`.
  `cy` is where the clip's CENTER sits: LOWER cy pushes the TOP off-frame; HIGHER cy (0.6) hides the bottom
  (burned-in subtitles). Check the result on the QA sheet - the wrong direction exposes the edge instead.
- **A wrong/garbled fragment** (voice mix-up, the other person finishing a line, a stray grunt):
  `{"clip":3,"kind":"cut","from":4.1,"to":5.0}` - fine when the story still reads without it.
- **Starts/ends too early or late:** `{"clip":1,"kind":"start","from":0.8}`, `{"clip":5,"kind":"end","to":8.9}`.
- **Clip 4 around the brand segment (story):** `{"clip":4,"kind":"pre","from":0,"to":1.0}` and
  `{"clip":4,"kind":"post","from":1.0,"to":10}`.
- **Podcast voice mix-ups:** `scripts/shot_audit.py beats/beatN beats/beatN/story.txt` lists every shot with the
  words spoken and who SHOULD say them, plus a thumbnail sheet. Face on screen != expected speaker = mix-up.
- **Gibberish CTA, missing lines, a wrong face:** the clip has to be made again. That's a new Riverio video run:
  quote it, ask, and only then run it.

## Captions
Speech recognition mishears brand names, drops "$" on prices and captions grunts. After every edit:
`fix_caps.py beats/beatN --brand "<Brand Name>" --fix <Misheard>=<Right> --price <n>` (`--dry-run` first to see
the changes). It refuses to export while a caption is still wrong.

## Palmier quirks
- Transcription may not be ready right after import -> spans come out empty/untrimmed. Just re-run.
- It only keeps a few projects/locales warm -> the scripts close open projects first.
- Closing projects or exporting can time out -> re-run the same command.
- "No speech detected" from captions over a silent stretch is harmless (the scripts skip it).
