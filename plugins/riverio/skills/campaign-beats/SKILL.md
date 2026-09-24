---
name: campaign-beats
description: Make new ad beats for a Riverio campaign by copying a finished beat - write the stories, clone its canvas, run it on Riverio (quoted and confirmed first), edit the clips in Palmier Pro, QA, and upload the finals after the user approves. Use when someone gives a Riverio campaign link and asks to copy/make/build beats or ads, e.g. "Campaign <url>, Part 2, copy beat 1 to beats 6-8".
---

# Campaign beats

The person you're helping is on the production crew, not a developer. Talk plainly: what you're doing, what it costs,
what you need from them. Don't show code, JSON or tool names unless they ask. One question at a time.

Tools: the **riverio** MCP tools (`get_campaign`, `get_brand_assets`, `clone_beat`, `quote_run`, `run_canvas`,
`run_status`, `get_outputs`, `prepare_upload`, `upload_final`) and the **palmier-pro** MCP tools (the video editor).
Scripts: `${CLAUDE_SKILL_DIR}/scripts/` - run them with `python3.12` (fall back to `python3`). Each prints `--help`.

## Hard rules
- **Money:** before ANY `run_canvas`, show the token cost from `quote_run` - agents and videos separately - and wait
  for a clear yes. Pass the exact quoted number as `confirmTokens`. A new run = a new quote = a new yes.
- **Uploads:** never `upload_final` until they have watched the finals and said yes ("upload", "yes, upload").
  Uploaded finals show up in the customer's gallery.
- **Videos run on Riverio only.** No other video services.
- **Music:** no song or music without a license. If unsure, leave it out.
- Never touch a canvas someone else is running (`run_status` first), and never edit the SOURCE beat's canvas.
- If a riverio tool errors with a key/permission problem, tell them to ask Eliad for a key. Don't work around it.

## Working folder
Everything for a campaign lives in `~/Riverio/<campaign-name>/` (short, lowercase, dashes):
`campaign.json`, `brand/` (logo, mascot, b-roll, end card), and one `beats/beatN/` per target beat holding
`story.txt`, `outputs.json`, `cast_*.png`, `clips/clip1..5.mp4`, `covers.json`, `final_9x16.mp4`, `final_3x4.mp4`,
`project.palmier`. Download with `curl -fsSL -o <file> "<url>"`.

## The recipe
1. **Understand the ask.** `get_campaign(url)`. Find the Part (concept), the source beat (ad idea) and the target
   beats; list their titles back and confirm in ONE question. The source must have a finished canvas.
   Save `campaign.json`. Work out the **style** from the source canvas's outputs (`get_outputs` on it):
   - **podcast** - two people talking at a desk; script in `CLIP k OF 5` blocks; b-roll on keywords; end card.
   - **story** - acted/cartoon scene; story in `BEAT 1..5:` blocks; a brand segment inside clip 4; end card.
   `get_brand_assets(campaignId)` -> download logo/mascot/b-roll into `brand/`.
2. **Write the stories.** One per target beat, in exactly the source's Prompt format and length (the source's
   `story` from `get_outputs` is your template). Read [writing.md](writing.md) first. Show ALL of them at once and
   ask for "yes" or edits. Save each as `beats/beatN/story.txt`.
3. **Clone.** `clone_beat(fromWorkflowId=<source>, toAdIdeaId, story)` per beat (videos stay off).
   Then `quote_run` each (returns `agentsTokens`, `videosTokens`, `allTokens`) and ask ONCE with the sums, e.g.
   *"Agents for 3 canvases: 231 tokens. Videos on Riverio after that: 2,100 tokens more. Run the agents now?"*
4. **Agents only.** `run_canvas(workflowId, mode:"agents", confirmTokens=<agentsTokens>)` per beat; poll
   `run_status` every ~30 s until done (report errors plainly). `get_outputs` -> save `outputs.json`, download
   character images to `cast_A.png`/`cast_B.png` and LOOK at them. Check before any video spend:
   - each character image is ONE clean character sheet: no storyboard panels, no text/subtitles, no collage;
     podcast: person A is the one who sits LEFT in the clip prompts.
   - `dialogue_check.py beats/beatN/story.txt beats/beatN/outputs.json` - every story line is in a clip prompt.
   If something's wrong, say what and offer a re-run of the agents (new quote, new yes). Don't start videos on bad inputs.
5. **Videos.** `quote_run` again and show the exact `videosTokens` (sum over beats); ask. On yes:
   `run_canvas(workflowId, mode:"videos", confirmTokens=<videosTokens>)` - runs ONLY the video nodes on the prompts
   you already checked (the agents are not re-run). The server refuses a wrong number: if it does, re-quote and ask again.
   Poll `run_status`, then `get_outputs` for the video URLs. Download the 5 videos in order to `clips/clip1..5.mp4`.
6. **Edit in Palmier.** Palmier Pro must be open with its MCP server on (`scripts/pal.py --ping`).
   Brand pieces first (end card, story style: brand segment - see [editing.md](editing.md)), then per beat:
   `edit_beat.py beats/beatN --style <podcast|story> --endcard brand/<end card> [...]`.
   Watch for problems and fix them with `covers.json` + re-run (details in [editing.md](editing.md)).
   Captions: `fix_caps.py beats/beatN --brand "<Brand Name>" --fix <Misheard>=<Right> --price <n>`.
7. **QA** every beat with [qa.md](qa.md) (`qa.sh`, `say_check.py`, look at `qa_sheet.jpg`). Fix, re-export, re-check.
8. **Show and wait.** Give them the final file paths (both ratios per beat) and ask them to watch. Change what they ask.
   Only after an explicit "upload": per beat and ratio, `prepare_upload(workflowId, filename, "video/mp4")` ->
   `curl -fsS -X PUT -H "Content-Type: video/mp4" --data-binary @final_9x16.mp4 "<uploadUrl>"` ->
   `upload_final(workflowId, ratio "9:16" | "3:4", fileUrl)`. Then `get_campaign` again and confirm each target beat
   shows 2 final videos. Tell them it's done, with the canvas links.

If you're lost or something doesn't match this recipe, stop and ask - don't improvise with money or uploads.
