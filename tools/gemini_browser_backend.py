#!/usr/bin/env python3
"""gemini_browser_backend.py — hero images on the AI Ultra SUBSCRIPTION.

Why this exists
---------------
Google runs two unrelated billing ledgers. AI Ultra ($249/mo, Google Play) covers
the Gemini *app*; the developer API (generativelanguage / Vertex) bills a Cloud
project. There is no key that makes the API bill against Ultra, and it is not a
configuration gap — it was probed directly on 2026-07-25:

  * Code Assist OAuth (the path :6543 uses, which DOES run on the Ultra
    allowance): text models return HTTP 200, every image model returns
    HTTP 404 "Requested entity was not found" on the identical envelope.
  * The same subscription token against generativelanguage returns
    HTTP 403 "Request had insufficient authentication scopes".
  * `agy models` lists 11 models, all text. No image plugin exists.
  * gemini-cli bundles generateImages, but only via ...FromVertex /
    ...FromMldev — both metered surfaces.

So the only way to spend the subscription on images is the surface the
subscription actually covers: the Gemini web app. This backend drives it with
agent-browser using a persistent Chrome profile.

Trade-off, stated plainly: this is the same ToS-grey class as the :6543
gemini-code-assist OAuth proxy (owner-accepted 2026-06-13). It automates a
human-facing UI with the operator's own logged-in session. It is deliberate,
not incidental.

Auth
----
One interactive Google login, once, into a dedicated profile:

    agent-browser --profile ~/.local/share/sanctum/browser-profiles/gemini \\
        open https://accounts.google.com/ServiceLogin?continue=https://gemini.google.com/app

The profile lives OUTSIDE every git repo on purpose — it holds live Google
session cookies. Never relocate it into ~/.sanctum or ~/.sanctum-mbp.

Design note
-----------
Selectors are resolved from the accessibility snapshot by ROLE + ACCESSIBLE NAME,
never by hardcoded @eN refs (those are regenerated per snapshot and go stale the
moment the page changes) and never by CSS (the Gemini app ships obfuscated
class names that rotate). If the UI moves, this fails LOUDLY with the snapshot
attached, so the next reader sees what actually changed.
"""
from __future__ import annotations

import argparse
import base64
import json
import pathlib
import re
import shutil
import subprocess
import sys
import time

PROFILE = pathlib.Path.home() / ".local/share/sanctum/browser-profiles/gemini"
GEMINI_URL = "https://gemini.google.com/app"
BIN = shutil.which("agent-browser") or "/opt/homebrew/bin/agent-browser"


class BrowserError(RuntimeError):
    """Raised with the snapshot attached so a UI change is self-diagnosing."""


def ab(*args: str, timeout: int = 180, check: bool = True) -> str:
    """Run one agent-browser command against the persistent profile."""
    cmd = [BIN, "--profile", str(PROFILE), *args]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if check and r.returncode != 0:
        raise BrowserError(f"agent-browser {' '.join(args[:2])} failed:\n{r.stderr.strip()[:400]}")
    return r.stdout


def snapshot() -> str:
    return ab("snapshot", "-i", "-c")


def find_ref(snap: str, role: str, name_re: str) -> str | None:
    """Resolve a @ref from the accessibility tree by role + accessible name."""
    rx = re.compile(rf'{role}\s+"([^"]*)"[^\]]*\[ref=(e\d+)\]')
    for m in rx.finditer(snap):
        if re.search(name_re, m.group(1), re.I):
            return "@" + m.group(2)
    return None


def ensure_signed_in(snap: str) -> None:
    if find_ref(snap, "button", r"^sign in$"):
        raise BrowserError(
            "Not signed in to Gemini in this profile. Run once, interactively:\n"
            f"  agent-browser --profile {PROFILE} \\\n"
            "      open 'https://accounts.google.com/ServiceLogin?continue=https://gemini.google.com/app'"
        )


def submit_prompt(prompt: str) -> None:
    ab("open", GEMINI_URL)
    time.sleep(3)
    snap = snapshot()
    ensure_signed_in(snap)

    box = find_ref(snap, "textbox", r"prompt for gemini|enter a prompt")
    if not box:
        raise BrowserError("prompt textbox not found. Snapshot:\n" + snap[:1500])

    # Say "generate an image" explicitly — the app routes to its image model on
    # intent, and an un-prefixed art description often returns prose about the
    # image instead of the image.
    ab("fill", box, f"Generate an image. {prompt}")
    ab("press", "Enter")


def wait_for_image(timeout_s: int = 300, poll_s: int = 10) -> str:
    """Poll until an <img> with real image data appears in the response.

    Returns the src (data: or https:). Raises with the last snapshot on timeout.
    """
    deadline = time.time() + timeout_s
    js = (
        "JSON.stringify(Array.from(document.querySelectorAll('img'))"
        ".map(i=>i.src).filter(s=>s&&(s.startsWith('data:image')"
        "||/googleusercontent|blob:/.test(s))))"
    )
    while time.time() < deadline:
        try:
            out = ab("eval", js, timeout=60)
            m = re.search(r"\[.*\]", out, re.S)
            if m:
                srcs = json.loads(m.group(0))
                # skip avatars/icons: real generations are large or data URLs
                for s in srcs:
                    if s.startswith("data:image") or "googleusercontent" in s:
                        if "=s32" in s or "=s64" in s or "avatar" in s.lower():
                            continue
                        return s
        except Exception:
            pass
        time.sleep(poll_s)
    raise BrowserError(
        f"no image after {timeout_s}s — the app may still be generating, or the "
        "response was text. Snapshot:\n" + snapshot()[:1500]
    )


def save_image(src: str, out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    if src.startswith("data:image"):
        out.write_bytes(base64.b64decode(src.split(",", 1)[1]))
        return
    # Fetch inside the page so the session cookie applies, then hand back base64.
    js = (
        "(async()=>{const r=await fetch(%s);const b=await r.arrayBuffer();"
        "return btoa(String.fromCharCode(...new Uint8Array(b)));})()" % json.dumps(src)
    )
    out_b64 = ab("eval", "--await", js, timeout=180)
    b64 = re.sub(r"[^A-Za-z0-9+/=]", "", out_b64)
    if len(b64) < 512:
        raise BrowserError(f"fetched image too small ({len(b64)} b64 chars) from {src[:80]}")
    out.write_bytes(base64.b64decode(b64))


def generate(prompt: str, out: pathlib.Path, timeout_s: int = 300) -> pathlib.Path:
    submit_prompt(prompt)
    src = wait_for_image(timeout_s)
    save_image(src, out)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--out", required=True, type=pathlib.Path)
    ap.add_argument("--timeout", type=int, default=300)
    ap.add_argument("--keep-open", action="store_true",
                    help="leave the browser running (useful while iterating)")
    a = ap.parse_args()

    if not PROFILE.exists():
        print(f"profile missing: {PROFILE}\nlog in once first (see module docstring)", file=sys.stderr)
        return 2
    try:
        p = generate(a.prompt, a.out, a.timeout)
    except BrowserError as e:
        print(f"FAILED: {e}", file=sys.stderr)
        return 1
    finally:
        if not a.keep_open:
            ab("close", check=False)
    size = p.stat().st_size
    print(f"OK {p} ({size} bytes)")
    return 0 if size > 10_000 else 1


if __name__ == "__main__":
    sys.exit(main())
