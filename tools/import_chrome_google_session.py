#!/usr/bin/env python3
"""Bootstrap the Gemini automation profile from Chrome — no password, no 2FA.

The Gemini web-app backend needs a logged-in Google session. Rather than
automate a Google password + 2FA prompt (storing the account's crown jewels,
tripping bot detection, and breaking on every login-flow change), this lifts the
session cookies Chrome ALREADY holds and loads them into the automation profile.

agent-browser's own guidance: reusing existing cookies "works for any site,
including those with complex OAuth flows, SSO, or 2FA, as long as Chrome already
has valid session cookies." That is the whole trick — we never see a credential,
only an already-granted session.

    ~/.sanctum/cli-venv/bin/python tools/import_chrome_google_session.py

⚠️ WHAT THIS HANDLES: live Google session cookies are equivalent in power to the
logged-in account. The intermediate state file is written 0600 to a temp path
outside every git repo and DELETED on the way out (even on failure). Nothing is
persisted except inside the Chrome profile that already needed to hold it.

Requires `cryptography` — present in ~/.sanctum/cli-venv, absent from system python.

═══ KNOWN LIMIT — READ BEFORE RELYING ON THIS (measured 2026-07-25) ═══
A RUNNING Chrome keeps its cookie jar in memory and flushes to disk lazily. On
the MBP the on-disk DB had not been written for EIGHT DAYS while Chrome ran with
a live, valid session. So this tool reads a stale snapshot, not the current
session.

Observed sequence: the stale cookies authenticated once; a stray navigation to a
non-existent /u/<n> account index signed that session out; and re-importing the
same on-disk values could no longer authenticate — clean profile, fresh import,
still signed out. The values on disk were simply dead.

Consequences:
  * Treat this as a BOOTSTRAP that works when Chrome has flushed (i.e. after
    Chrome has been quit), NOT as a refresh mechanism for a running browser.
  * Do NOT probe /u/0, /u/1, /u/2 to hunt for a multi-account index. An index
    with no corresponding account signs the session out. Use the in-page account
    switcher instead.

The reliable alternatives, in order:
  1. One interactive login into the automation profile. Google sessions persist
     for months and refresh on use, so this is a single manual step, ever — and
     it stores no credential anywhere.
  2. `agent-browser --auto-connect state save` against a Chrome started with
     --remote-debugging-port. This reads LIVE in-memory session state, so no
     staleness — at the cost of a debug port that lets any local process drive
     the browser and read its cookies. On a host running many agents that is a
     real exposure; weigh it deliberately.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import shutil
import sqlite3
import subprocess
import sys
import tempfile

CHROME_DEFAULT = pathlib.Path.home() / "Library/Application Support/Google/Chrome/Default"
PROFILE = pathlib.Path.home() / ".local/share/sanctum/browser-profiles/gemini"
BIN = shutil.which("agent-browser") or "/opt/homebrew/bin/agent-browser"
# Chrome's macOS cookie KDF — fixed constants, not secrets.
SALT, ITERATIONS, KEYLEN, IV = b"saltysalt", 1003, 16, b" " * 16


def safe_storage_key() -> bytes:
    r = subprocess.run(["security", "find-generic-password", "-s", "Chrome Safe Storage", "-w"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit("could not read the 'Chrome Safe Storage' keychain item")
    return r.stdout.strip().encode()


def derive(pw: bytes) -> bytes:
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    return PBKDF2HMAC(algorithm=hashes.SHA1(), length=KEYLEN,
                      salt=SALT, iterations=ITERATIONS).derive(pw)


def decrypt(blob: bytes, key: bytes) -> str | None:
    """Decrypt a Chrome v10 cookie value."""
    if not blob or not blob.startswith(b"v10"):
        return blob.decode(errors="replace") if blob else ""
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    dec = Cipher(algorithms.AES(key), modes.CBC(IV)).decryptor()
    try:
        raw = dec.update(blob[3:]) + dec.finalize()
    except Exception:
        return None
    if raw and raw[-1] <= 16:                      # strip PKCS7 padding
        raw = raw[: -raw[-1]]
    for candidate in (raw, raw[32:]):              # newer Chrome prefixes a 32-byte domain hash
        try:
            s = candidate.decode("utf-8")
            if s.isprintable() or not s:
                return s
        except UnicodeDecodeError:
            continue
    return None


def collect(host_like: str = "%google.com") -> list[dict]:
    key = derive(safe_storage_key())
    tmpdb = pathlib.Path(tempfile.mkdtemp()) / "Cookies"
    shutil.copy2(CHROME_DEFAULT / "Cookies", tmpdb)   # copy: the live DB is locked
    try:
        con = sqlite3.connect(f"file:{tmpdb}?immutable=1", uri=True)
        rows = con.execute(
            "SELECT host_key,name,encrypted_value,path,expires_utc,is_secure,is_httponly,samesite"
            " FROM cookies WHERE host_key LIKE ?", (host_like,)).fetchall()
    finally:
        shutil.rmtree(tmpdb.parent, ignore_errors=True)

    out, failed = [], 0
    for host, name, enc, path, exp, secure, httponly, samesite in rows:
        val = decrypt(enc, key)
        if val is None:
            failed += 1
            continue
        # Chrome epoch (1601) microseconds -> unix seconds; 0 means session cookie
        expires = (exp / 1_000_000 - 11_644_473_600) if exp else -1
        out.append({
            "name": name, "value": val, "domain": host, "path": path or "/",
            "expires": expires, "httpOnly": bool(httponly), "secure": bool(secure),
            "sameSite": {0: "None", 1: "Lax", 2: "Strict"}.get(samesite, "Lax"),
        })
    if failed:
        print(f"  note: {failed} cookie(s) failed to decrypt (skipped)", file=sys.stderr)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", type=pathlib.Path, default=PROFILE)
    ap.add_argument("--host-like", default="%google.com")
    ap.add_argument("--dry-run", action="store_true", help="report what would be imported")
    a = ap.parse_args()

    if not (CHROME_DEFAULT / "Cookies").exists():
        sys.exit(f"no Chrome cookie DB at {CHROME_DEFAULT}")

    cookies = collect(a.host_like)
    if not cookies:
        sys.exit("no matching cookies — is Chrome signed in to Google?")
    hosts = sorted({c["domain"] for c in cookies})
    auth = [c["name"] for c in cookies if c["name"] in
            ("SID", "SSID", "HSID", "SAPISID", "APISID", "__Secure-1PSID", "__Secure-3PSID")]
    print(f"collected {len(cookies)} cookies across {len(hosts)} hosts")
    print(f"  session-bearing cookies present: {auth or 'NONE — import will not authenticate'}")
    if a.dry_run:
        return 0
    if not auth:
        sys.exit("refusing to import: no session cookies found (Chrome may be signed out)")

    fd, tmp = tempfile.mkstemp(suffix=".json", prefix="gsess-")
    os.close(fd)
    tmp = pathlib.Path(tmp)
    try:
        os.chmod(tmp, 0o600)
        tmp.write_text(json.dumps({"cookies": cookies, "origins": []}))
        a.profile.mkdir(parents=True, exist_ok=True)
        subprocess.run([BIN, "--profile", str(a.profile), "open", "about:blank"],
                       capture_output=True, timeout=120)
        r = subprocess.run([BIN, "--profile", str(a.profile), "state", "load", str(tmp)],
                           capture_output=True, text=True, timeout=120)
        if r.returncode != 0:
            sys.exit(f"state load failed: {r.stderr.strip()[:300]}")
        print("state loaded into the automation profile")
    finally:
        tmp.unlink(missing_ok=True)          # never leave session tokens on disk
    return 0


if __name__ == "__main__":
    sys.exit(main())
