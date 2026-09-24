# Riverio for Claude

This lets Claude (the desktop app, **Code** tab) make new ads for a Riverio campaign for you, start to finish:
it writes the new stories, copies a finished ad's canvas, runs it on Riverio, edits the videos in Palmier Pro,
checks them, and uploads the finished videos once you've watched them and said yes.

## One-time setup (about 15 minutes)

You need: a Mac on **macOS 26 or newer**, the **Claude** desktop app signed in, and your **Riverio key**
(Eliad gives you this - it starts with `sk_`; keep it private, like a password).

1. Download this project: green **Code** button above -> **Download ZIP**. Open the ZIP.
2. In the `install` folder, **double-click `install.command`**.
   (If your Mac says it can't be opened: right-click it -> **Open** -> **Open**.)
3. Follow the window. It installs the tools it needs, installs Palmier Pro, asks for your Riverio key
   (you won't see it while you paste - that's normal), and adds the Riverio plugin to Claude.
   If it says it couldn't add the plugin, open Claude -> **Code** tab and send these two lines, one at a time:
   ```
   /plugin marketplace add GambitCreativeltd/riverio-claude-plugin
   /plugin install riverio@riverio
   ```
4. Open **Palmier Pro** once and turn on its **MCP server** in its settings. Keep Palmier open while Claude edits.
5. Quit Claude (Cmd+Q) and open it again.

You can run `install.command` again any time; it skips what's already done.

## How to ask

Open Claude -> **Code** tab -> choose a folder (your home folder is fine) and write what you want, like:

> Campaign https://studio.riverio.ai/... , Part 2, copy beat 1 to beats 6-8

Claude will:
1. Read the campaign and check with you: which Part, which beat to copy, which beats to make.
2. Write a story for each new beat and show them all to you. Say **yes** or tell it what to change.
3. Tell you what running the canvases costs, and wait for your yes.
4. Make the characters and scenes, check them, then tell you what the videos cost, and wait for your yes.
5. Edit each ad in Palmier (captions, brand segment, end card), check sound, captions and the call to action.
6. Give you the finished videos (tall 9:16 and 3:4) to watch. Nothing is uploaded until you say **upload**.

Your files are in the **Riverio** folder in your home folder (one folder per campaign).

## Costs

Everything that runs on Riverio uses **tokens**. Claude always tells you the price first - the AI agents
(stories, characters, prompts) and the videos separately - and waits for your OK. The videos are the
expensive part. If something fails, tell Claude; it will say what a re-run costs before doing it.
Editing in Palmier and the checks on your Mac are free.

## If something goes wrong

- "Can't reach Palmier Pro" -> open Palmier Pro and turn on its MCP server.
- Claude says the Riverio key doesn't work -> ask Eliad for a new key, then run `install.command` again.
- Anything else -> screenshot and send to Eliad.

## For maintainers

- `plugins/riverio/.mcp.json` - the Riverio MCP server (`https://studio.riverio.ai/api/mcp`, key from the
  `RIVERIO_API_KEY` environment variable, which the installer puts in `~/.claude/settings.json` -> `env`) and
  Palmier Pro's local MCP server (`http://127.0.0.1:19789/mcp`).
- `plugins/riverio/skills/campaign-beats/` - the recipe (`SKILL.md` + `writing.md`, `editing.md`, `qa.md`) and
  its scripts (Python 3 standard library + ffmpeg only).
- `install/install.command --dry-run` shows what the installer would do without changing anything.
- Validate: `claude plugin validate .` and `claude plugin validate plugins/riverio`.
