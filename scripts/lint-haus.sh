#!/usr/bin/env bash
# lint-haus.sh — Find stray "home" and "house" that should be "haus"
#
# Usage:
#   ./scripts/lint-haus.sh              # Lint all docs
#   ./scripts/lint-haus.sh path/to.mdx  # Lint specific file or directory
#   ./scripts/lint-haus.sh --self-test  # Verify positive & negative cases
#
# Exits 0 if clean, 1 if violations found, 2 on internal/runtime error.
# Implemented in Python (never BSD `grep -P`, which exits 2 on macOS).

set -euo pipefail

DOCS_DIR="src/content/docs"
TARGET="${1:-$DOCS_DIR}"

exec python3 -I - "$TARGET" <<'PY'
import os
import re
import sys
import tempfile
from pathlib import Path

RED = "\033[0;31m"
YELLOW = "\033[0;33m"
GREEN = "\033[0;32m"
NC = "\033[0m"

# Contexts where "home" or "house" is a product name, OS/filesystem concept,
# standard English category/idiom, or preserved page title — NOT a noun for
# this specific dwelling running Sanctum (see CONTRIBUTING.md § The Haus Rule).
ALLOW_PATTERNS = [
    # Product & UI names
    r"Home Assistant",
    r"HomeKit",
    r"Apple Home",
    r"Home Companion",
    r"home-assistant",
    r"Health Auto Export",
    r"Home screen",
    r"docs home",
    r"Home Network",
    # File paths, env vars, CLI subcommands, & OS user home directory concepts
    r"/home/",
    r"sanctum_home",
    r"DOCKER_HOST",
    r"house-pulse",
    r"HOUSE-BIBLE",
    r"\$HOME\b",
    r"sanctum net home",
    r"Start with \*\*home\*\*",
    r"home directory",
    r"MBP home",
    r"operator home",
    r"Mac home",
    r"configured\*? home",
    r"host home tree",
    r"home path",
    r"home[- ]resolution",
    r"user's (?:own )?home",
    r"SanctumBridge's home",
    r"per-home",
    r"disposable (?:Sanctum )?home",
    r"control home directly",
    r"single full-suite run home",
    r"\*?(?:intended|correct|bad|one)\*? home\b",
    r"the home of\b",
    r"at home on Linux",
    r"home addresses",
    r"home (?:LAN|Wi-Fi|lease)\b",
    r"^home and a daily integrity check",
    # Standard English category & networking terms
    r"home[- ]office",
    r"home[- ]router",
    r"home[- ]server",
    r"home[- ]network",
    r"Home energy",
    r"home_assistant",
    r"ghcr\.io/home",
    r"Home automation \(HA\)",
    r"Home automation \.HA\.",
    r"phone[- ]home",
    r"phoned? home",
    r"phones home",
    r"phoning home",
    r"report home",
    r"in-house",
    r"whole-house TTS",
    r"house style",
    # Idioms, generic analogies, presence predicates, & fictional tournament houses
    r"a house that lost power",
    r"smoke alarm fails honestly in an empty house",
    r"house calls",
    r"house is on fire",
    r"burning your house down",
    r"decision to make about a house",
    r"Two small houses",
    r"manor house",
    r"wrong house card",
    r"man lets AI agents manage home",
    r"House Winterfang",
    r"House Goldclaw",
    r"Nine Houses",
    r"great houses",
    r"Per-house",
    r"\b(?:come|comes|came|gone|stayed|stay|carry one good commit) home\b",
    r"\b(?:found|finding) its home\b",
    r"\b(?:nobody|anyone|who's|smith|family)\b.{0,12}\bhome\b",
    r"\bis anyone home\b",
    r"\bsitting at home\b",
    # Preserved frontmatter page titles (renaming slugs breaks inbound links)
    r"^title:\s*",
]

ALLOW_RE = re.compile("|".join(f"(?:{p})" for p in ALLOW_PATTERNS), re.IGNORECASE)
WORD_RE = re.compile(r"\b(home|house)\b", re.IGNORECASE)
INLINE_CODE_RE = re.compile(r"`[^`]*`")
MD_LINK_TARGET_RE = re.compile(r"(\]\()([^)]+)(\))")


def lint_file(path: Path) -> list[tuple[int, str]]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    flagged: list[tuple[int, str]] = []
    in_fence = False
    for idx, raw in enumerate(lines, 1):
        stripped = raw.lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        cleaned = INLINE_CODE_RE.sub(" ", raw)
        cleaned = MD_LINK_TARGET_RE.sub(r"\1\3", cleaned)
        if not WORD_RE.search(cleaned):
            continue
        # Handle line-wrapped "Home\nAssistant"
        joined = raw
        if idx < len(lines):
            joined = f"{raw} {lines[idx].lstrip()}"
        if ALLOW_RE.search(raw) or ALLOW_RE.search(cleaned) or ALLOW_RE.search(joined):
            continue
        flagged.append((idx, raw))
    return flagged


def collect_files(target: Path) -> list[Path]:
    if target.is_file():
        return [target]
    if target.is_dir():
        return sorted(
            p for p in target.rglob("*")
            if p.is_file() and p.suffix.lower() in (".md", ".mdx")
        )
    print(f"lint-haus: target does not exist: {target}", file=sys.stderr)
    raise SystemExit(2)


def run_self_test() -> int:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        bad = root / "bad.mdx"
        bad.write_text(
            "---\ntitle: Test\n---\n"
            "The house lights turned on when we got home.\n"
            "A home automation system that unilaterally kills the lights.\n",
            encoding="utf-8",
        )
        hits_bad = lint_file(bad)
        if len(hits_bad) != 2:
            print(f"SELF-TEST FAIL: expected 2 violations on bad.mdx, got {len(hits_bad)}: {hits_bad}", file=sys.stderr)
            return 2

        good = root / "good.mdx"
        good.write_text(
            "---\ntitle: \"2026-07-11: CI comes home\"\n---\n"
            "Home Assistant runs alongside `sanctum net home` and `/home/ubuntu`.\n"
            "```bash\n"
            "echo \"$HOME/house\"\n"
            "```\n"
            "See [the old note](/operations/2026-06-29-the-form-that-could-wipe-the-house/).\n",
            encoding="utf-8",
        )
        hits_good = lint_file(good)
        if hits_good:
            print(f"SELF-TEST FAIL: expected 0 violations on good.mdx, got {hits_good}", file=sys.stderr)
            return 2

    print(f"{GREEN}lint-haus self-test: PASS{NC} (positive repro caught, allowed contexts clean)")
    return 0


def main() -> int:
    arg = sys.argv[1]
    if arg == "--self-test":
        return run_self_test()

    files = collect_files(Path(arg))
    violations = 0
    for f in files:
        hits = lint_file(f)
        if hits:
            print(f"{RED}{f}{NC}")
            for lineno, line in hits:
                print(f"  {YELLOW}{lineno}:{line}{NC}")
            print("")
            violations += len(hits)

    print("───────────────────────────────────")
    print(f"Files checked: {len(files)}")
    if violations > 0:
        print(f"Violations:    {RED}{violations}{NC}")
        print("")
        print("Review each hit — some may be intentional (idioms, generic analogies).")
        print("If it refers to THIS dwelling running Sanctum, change to 'haus'.")
        print("See CONTRIBUTING.md § The Haus Rule for the full policy.")
        return 1
    print(f"Violations:    {GREEN}0{NC} — all clear.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
PY
