#!/usr/bin/env python3
"""Tiny Palmier Pro MCP client over HTTP, for the bulk scripts (edit_beat.py, fix_caps.py, ...).
In chat, Claude uses the palmier-pro MCP tools directly; scripts use this so a long edit runs in one go.

usage: pal.py <tool> '<json args>'     call one tool and print the result
       pal.py --new                    start a fresh session
       pal.py --ping                   check that Palmier Pro is open with its MCP server on

Palmier URL: $PALMIER_MCP_URL (default http://127.0.0.1:19789/mcp).
The session id is kept in ~/Riverio/.pal_session so the open project survives between calls."""
import json
import os
import sys
import urllib.error
import urllib.request
os.environ["PATH"] = os.environ.get("PATH", "") + ":/opt/homebrew/bin:/usr/local/bin"  # Homebrew ffmpeg when launched from the app

URL = os.environ.get("PALMIER_MCP_URL", "http://127.0.0.1:19789/mcp")
SESS = os.path.join(os.path.expanduser("~/Riverio"), ".pal_session")
H = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}


class PalmierError(RuntimeError):
    pass


def post(body, sid=None):
    h = dict(H)
    if sid:
        h["Mcp-Session-Id"] = sid
    req = urllib.request.Request(URL, data=json.dumps(body).encode(), headers=h, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            raw = r.read().decode()
            new_sid = r.headers.get("Mcp-Session-Id")
    except urllib.error.URLError as e:
        raise PalmierError(f"Can't reach Palmier Pro at {URL}. Open Palmier Pro and turn on its MCP server. ({e})")
    msgs = [json.loads(l[5:]) for l in raw.splitlines() if l.startswith("data:") and l[5:].strip()]
    if not msgs and raw.strip().startswith("{"):
        msgs = [json.loads(raw)]
    return msgs, new_sid


def session(new=False):
    if not new and os.path.exists(SESS):
        return open(SESS).read().strip()
    _, sid = post({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                   "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                              "clientInfo": {"name": "riverio-campaign-beats", "version": "1"}}})
    post({"jsonrpc": "2.0", "method": "notifications/initialized"}, sid)
    os.makedirs(os.path.dirname(SESS), exist_ok=True)
    open(SESS, "w").write(sid or "")
    return sid


def call(tool, args, retry=True):
    sid = session()
    msgs, _ = post({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": tool, "arguments": args}}, sid)
    res = [m for m in msgs if "result" in m or "error" in m]
    if retry and (not res or ("error" in res[-1] and "session" in json.dumps(res[-1]).lower())):
        session(new=True)
        return call(tool, args, retry=False)
    return res[-1] if res else {"error": {"message": f"no reply from Palmier for {tool}"}}


def j(tool, args=None):
    """Call a Palmier tool; return parsed JSON (or text). Raise PalmierError on a tool error."""
    r = call(tool, args or {})
    if "error" in r:
        raise PalmierError(f"{tool}: {r['error'].get('message', r['error'])}")
    res = r.get("result", r)
    txt = "".join(c.get("text", "") for c in res.get("content", []) if c.get("type") == "text")
    if res.get("isError"):
        raise PalmierError(f"{tool}: {txt[:500]}")
    try:
        return json.loads(txt)
    except Exception:
        return txt


def close_open_projects():
    """Palmier's local transcription only keeps a few locales/projects warm; close old ones first.
    PAL_KEEP_OPEN=1 skips this (for testing next to someone's open project)."""
    if os.environ.get("PAL_KEEP_OPEN"):
        return
    for p in j("manage_project", {"action": "list"}).get("projects", []):
        if p.get("isOpen"):
            j("manage_project", {"action": "close", "id": p["id"]})


def wait_export(job, tries=150):
    import time
    ex = {}
    for _ in range(tries):
        time.sleep(4)
        ex = next((e for e in j("manage_exports", {"action": "list"})["exports"] if e["jobId"] == job), {})
        if ex.get("status") in ("completed", "failed", "cancelled"):
            break
    if ex.get("status") != "completed":
        raise PalmierError(f"export did not finish: {ex}")
    return ex


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(2)
    if sys.argv[1] == "--new":
        print(session(new=True)); sys.exit()
    if sys.argv[1] == "--ping":
        try:
            session(new=True); print(f"Palmier Pro MCP is up at {URL}")
        except PalmierError as e:
            print(e); sys.exit(1)
        sys.exit()
    out = call(sys.argv[1], json.loads(sys.argv[2]) if len(sys.argv) > 2 else {})
    r = out.get("result", out) if isinstance(out, dict) else out
    if isinstance(r, dict) and "content" in r:
        for c in r["content"]:
            if c.get("type") == "text":
                print(c["text"])
            elif c.get("type") == "image":
                import base64, tempfile, time
                p = os.path.join(tempfile.gettempdir(), f"pal_{int(time.time() * 1000)}.{c.get('mimeType', 'image/png').split('/')[-1]}")
                open(p, "wb").write(base64.b64decode(c["data"]))
                print(f"[image saved {p}]")
            else:
                print(f"[{c.get('type')} content]")
        if r.get("isError"):
            sys.exit(1)
    else:
        print(json.dumps(r, indent=1)[:20000])
