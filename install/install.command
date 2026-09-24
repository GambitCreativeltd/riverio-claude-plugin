#!/bin/bash
# Riverio crew setup for the Claude desktop app (Code tab).
# Double-click this file in Finder. Safe to run again: anything already done is skipped.
#   --dry-run   show what would happen, change nothing
set -u

REPO="GambitCreativeltd/riverio-claude-plugin"
PLUGIN="riverio@riverio"
PALMIER_DMG_URL="https://github.com/palmier-io/palmier-pro/releases/latest/download/PalmierPro.dmg"
SETTINGS="$HOME/.claude/settings.json"
DRY=0
[ "${1:-}" = "--dry-run" ] && DRY=1

say()  { printf '\n\033[1m%s\033[0m\n' "$*"; }
info() { printf '   %s\n' "$*"; }
ok()   { printf '   \033[32m✓\033[0m %s\n' "$*"; }
warn() { printf '   \033[33m!\033[0m %s\n' "$*"; }
run()  { if [ $DRY = 1 ]; then printf '   [dry-run] would run: %s\n' "$*"; else "$@"; fi; }
bye()  { printf '\n%s\n' "$*"; [ $DRY = 1 ] || { printf '\nPress Return to close this window.'; read -r _; }; exit 1; }

clear 2>/dev/null
say "Riverio setup for Claude"
info "This sets up: Homebrew, ffmpeg, Python, Palmier Pro, your Riverio key, and the Riverio plugin for Claude."
[ $DRY = 1 ] && info "(dry run: nothing will be changed)"

# 1. macOS version ---------------------------------------------------------------------------
say "1/6  Checking your Mac"
MACOS=$(sw_vers -productVersion 2>/dev/null || echo 0)
MAJOR=${MACOS%%.*}
if [ "${MAJOR:-0}" -lt 26 ]; then
  bye "Palmier Pro needs macOS 26 or newer. This Mac has macOS $MACOS. Update macOS (System Settings > General > Software Update) and run this again."
fi
ok "macOS $MACOS"

# 2. Homebrew + ffmpeg + python -------------------------------------------------------------
say "2/6  Homebrew, ffmpeg and Python"
BREW=""
for b in /opt/homebrew/bin/brew /usr/local/bin/brew "$(command -v brew 2>/dev/null)"; do
  [ -n "$b" ] && [ -x "$b" ] && { BREW="$b"; break; }
done
if [ -z "$BREW" ]; then
  info "Installing Homebrew (the Mac's app installer for tools). It will ask for your Mac password - that's normal."
  run /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  for b in /opt/homebrew/bin/brew /usr/local/bin/brew; do [ -x "$b" ] && BREW="$b"; done
  [ $DRY = 1 ] && BREW="${BREW:-/opt/homebrew/bin/brew}"
  [ -z "$BREW" ] && bye "Homebrew didn't install. Take a screenshot of this window and send it to Eliad."
else
  ok "Homebrew is already installed"
fi
[ $DRY = 1 ] || eval "$("$BREW" shellenv)"
for pkg in ffmpeg python@3.12; do
  if [ -x "$BREW" ] && "$BREW" list --versions "$pkg" >/dev/null 2>&1; then
    ok "$pkg is already installed"
  else
    info "Installing $pkg (a few minutes)..."
    run "$BREW" install "$pkg" || bye "Installing $pkg failed. Take a screenshot and send it to Eliad."
  fi
done

# Python for the steps below: Homebrew's (the Mac's own /usr/bin/python3 may pop up a developer-tools installer)
PY=""
for p in "$([ -x "$BREW" ] && "$BREW" --prefix 2>/dev/null)/bin/python3.12" /opt/homebrew/bin/python3.12 /usr/local/bin/python3.12 "$(command -v python3 2>/dev/null)"; do
  [ -n "$p" ] && [ -x "$p" ] && { PY="$p"; break; }
done
[ -z "$PY" ] && [ $DRY = 1 ] && PY=python3
[ -z "$PY" ] && bye "Python didn't install. Take a screenshot of this window and send it to Eliad."
# Pillow draws the price card (scripts/price_card.py)
if [ $DRY = 0 ] && "$PY" -c "import PIL" >/dev/null 2>&1; then
  ok "Pillow is already installed"
else
  info "Installing Pillow (image library)..."
  run "$PY" -m pip install --user --break-system-packages --quiet pillow || bye "Installing Pillow failed. Take a screenshot and send it to Eliad."
fi

# 3. Palmier Pro --------------------------------------------------------------------------------
say "3/6  Palmier Pro (the video editor)"
if [ -d "/Applications/PalmierPro.app" ] || [ -d "/Applications/Palmier Pro.app" ]; then
  ok "Palmier Pro is already in Applications"
else
  TMPD=$(mktemp -d 2>/dev/null || echo /tmp/palmier.$$)
  DMG="$TMPD/PalmierPro.dmg"
  info "Downloading Palmier Pro..."
  run curl -fL --progress-bar -o "$DMG" "$PALMIER_DMG_URL" || bye "Couldn't download Palmier Pro. Check your internet and try again."
  if [ $DRY = 1 ]; then
    run hdiutil attach -nobrowse -readonly "$DMG"
    run cp -R "<mounted disk>/PalmierPro.app" /Applications/
    run hdiutil detach "<mounted disk>"
  else
    MNT=$(hdiutil attach -nobrowse -readonly "$DMG" | awk -F'\t' '/\/Volumes\//{print $NF}' | tail -1)
    [ -z "$MNT" ] && bye "Couldn't open the Palmier Pro download."
    APP=$(find "$MNT" -maxdepth 1 -name "*.app" | head -1)
    [ -z "$APP" ] && { hdiutil detach "$MNT" -quiet; bye "No app found inside the Palmier Pro download."; }
    cp -R "$APP" /Applications/ || { hdiutil detach "$MNT" -quiet; bye "Couldn't copy Palmier Pro to Applications."; }
    hdiutil detach "$MNT" -quiet
    rm -rf "$TMPD"
    ok "Palmier Pro installed in Applications"
  fi
fi

# 4. Riverio key -> ~/.claude/settings.json (env.RIVERIO_API_KEY) ------------------------------
say "4/6  Your Riverio key"
HAVE_KEY=0
if [ -f "$SETTINGS" ] && "$PY" -c 'import json,sys; sys.exit(0 if json.load(open(sys.argv[1])).get("env",{}).get("RIVERIO_API_KEY") else 1)' "$SETTINGS" 2>/dev/null; then
  HAVE_KEY=1
fi
ASK=1
if [ $HAVE_KEY = 1 ]; then
  if [ $DRY = 1 ]; then
    info "A Riverio key is already saved. (would ask: replace it?)"; ASK=0
  else
    printf '   A Riverio key is already saved. Replace it? [y/N] '; read -r yn
    case "$yn" in [yY]*) ASK=1 ;; *) ASK=0; ok "Keeping the saved key" ;; esac
  fi
fi
if [ $ASK = 1 ]; then
  if [ $DRY = 1 ]; then
    info "[dry-run] would ask for the key (typing hidden), back up $SETTINGS,"
    info "          and save it as env.RIVERIO_API_KEY (other settings untouched, file readable only by you)"
  else
    info "Paste the Riverio key Eliad gave you (starts with sk_). You won't see it as you type - that's on purpose."
    KEY=""
    while [ -z "$KEY" ]; do
      printf '   Key: '; read -rs KEY; echo
      KEY=$(printf '%s' "$KEY" | tr -d '[:space:]')
      case "$KEY" in sk_*) ;; "") warn "Nothing pasted, try again." ;; *) warn "That doesn't start with sk_. Try again."; KEY="" ;; esac
    done
    mkdir -p "$HOME/.claude"
    [ -f "$SETTINGS" ] && { BK="$SETTINGS.backup-$(date +%Y%m%d-%H%M%S)"; cp -p "$SETTINGS" "$BK"; chmod 600 "$BK"; }
    RIVERIO_KEY="$KEY" "$PY" - "$SETTINGS" <<'PY' || bye "Couldn't save the key. Your old settings are backed up next to $SETTINGS."
import json, os, sys
p = sys.argv[1]
try:
    s = json.load(open(p)) if os.path.exists(p) and os.path.getsize(p) else {}
except ValueError:
    sys.exit("settings.json isn't valid JSON; not touching it")
if not isinstance(s, dict):
    sys.exit("settings.json isn't a JSON object; not touching it")
env = s.get("env") if isinstance(s.get("env"), dict) else {}
env["RIVERIO_API_KEY"] = os.environ["RIVERIO_KEY"]
s["env"] = env
tmp = p + ".tmp"
with open(tmp, "w") as f:
    json.dump(s, f, indent=2)
    f.write("\n")
os.chmod(tmp, 0o600)
os.replace(tmp, p)
PY
    chmod 600 "$SETTINGS"
    unset KEY
    ok "Key saved (only your user can read that file; the old one is backed up)"
  fi
fi

# 5. Plugin -----------------------------------------------------------------------------------
say "5/6  The Riverio plugin for Claude"
CLAUDE=""
for c in "$(command -v claude 2>/dev/null)" "$HOME/.local/bin/claude" /opt/homebrew/bin/claude /usr/local/bin/claude; do
  [ -n "$c" ] && [ -x "$c" ] && { CLAUDE="$c"; break; }
done
if [ -z "$CLAUDE" ]; then  # the desktop app keeps its own copy of Claude Code
  CLAUDE=$(ls -d "$HOME/Library/Application Support/Claude/claude-code/"*/claude.app/Contents/MacOS/claude 2>/dev/null | sort -V | tail -1)
fi
PASTE1="/plugin marketplace add $REPO"
PASTE2="/plugin install $PLUGIN"
MANUAL=0
if [ -n "$CLAUDE" ]; then
  info "Using Claude Code at: $CLAUDE"
  if [ $DRY = 1 ]; then
    run "$CLAUDE" plugin marketplace add "$REPO"
    run "$CLAUDE" plugin install "$PLUGIN" --scope user
  else
    if "$CLAUDE" plugin marketplace add "$REPO" >/dev/null 2>&1 || "$CLAUDE" plugin marketplace update riverio >/dev/null 2>&1; then
      ok "Riverio marketplace added"
      if "$CLAUDE" plugin install "$PLUGIN" --scope user; then ok "Riverio plugin installed"; else MANUAL=1; fi
    else
      MANUAL=1
    fi
  fi
else
  MANUAL=1
fi
if [ $MANUAL = 1 ]; then
  warn "Couldn't add the plugin automatically. Do it in Claude instead:"
  info "Open Claude > Code tab, and send these two lines, one at a time:"
  echo
  echo "      $PASTE1"
  echo "      $PASTE2"
fi

# 6. Checklist ----------------------------------------------------------------------------------
say "6/6  Almost done - three things to do by hand"
cat <<EOF
   1. Open Palmier Pro once (Applications > Palmier Pro). In its settings, turn ON the MCP server
      (Claude talks to Palmier through it). Keep Palmier open while Claude edits.
   2. Quit Claude completely (Cmd+Q) and open it again, so it picks up your key and the plugin.
   3. In Claude, open the Code tab, pick a folder (your home folder is fine) and type, for example:

        Campaign https://studio.riverio.ai/<the campaign link>, Part 2, copy beat 1 to beats 6-8

      Claude will ask before it spends anything, and before it uploads anything.
      Your work is saved in the Riverio folder in your home folder.
EOF
[ $DRY = 1 ] && { echo; echo "(dry run finished - nothing was changed)"; exit 0; }
printf '\nAll set. Press Return to close this window.'; read -r _
