#!/usr/bin/env python3
"""contrib-check.py — enforce CONTRIBUTING.md rules on sanctum-docs pages.

Walks every .mdx under src/content/docs/** and reports violations of the
rules in CONTRIBUTING.md that can be mechanically verified. Rules that
require human judgement (tone, haus-vs-house context, ASCII-art mobile
rendering) are deliberately NOT automated — they belong in the PR review.

Exit 0 if all checks pass, exit 1 if any error. Warnings don't fail the
build but print to stdout.

Usage:
    python3 scripts/contrib-check.py              # check everything
    python3 scripts/contrib-check.py path/to.mdx  # check one file
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "src" / "content" / "docs"

# Emoji ranges (common pictographic blocks). Excludes ASCII punctuation.
# Keeps whitespace/ideographs out by bounding to the pictograph planes.
EMOJI_RE = re.compile(
    r'[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F000-\U0001F2FF]'
)

# Strip code fences before scanning prose-only rules.
CODE_BLOCK_RE = re.compile(r'```.*?```', re.S)
INLINE_CODE_RE = re.compile(r'`[^`]*`')
IMAGE_REF_RE = re.compile(r'!\[([^\]]*)\]\(([^)]+)\)')
FRONTMATTER_RE = re.compile(r'^---\n(.*?)\n---\n?', re.S)

# Placeholder tokens CONTRIBUTING.md flags as a failing offense.
PLACEHOLDER_TOKENS = [
    "example.com",
    "YOUR_TOKEN",
    "YOUR_API_KEY",
    "YOUR_KEY_HERE",
    "<placeholder>",
    "TODO_ME",
    "lorem ipsum",
]

# Pages allowed to use emojis (the "Holocron portal" exemption).
# Only the landing pages are exempt — these carry the semantic brand
# glyphs (fleur-de-lis, black bear) that mark the QC identity of the
# haus. Regular content pages stay emoji-free; use words instead
# (RUN / FAIL / FLAP) for status, not checkmarks.
EMOJI_ALLOW = {
    "index.mdx",
    "index-qc.mdx",
    "qc.mdx",
}


class Report:
    def __init__(self):
        self.errors = []
        self.warnings = []

    def err(self, path, line, rule, msg):
        self.errors.append(f"{path}:{line}: [{rule}] {msg}")

    def warn(self, path, line, rule, msg):
        self.warnings.append(f"{path}:{line}: [{rule}] {msg}")


def body_starts_at(content, fm_end_idx):
    """Line number (1-indexed) where the body begins after frontmatter."""
    return content.count("\n", 0, fm_end_idx) + 1


def check_frontmatter(path, rel, content, report):
    fm_m = FRONTMATTER_RE.match(content)
    if not fm_m:
        report.err(rel, 1, "frontmatter", "no YAML frontmatter at top of file")
        return None
    fm_body = fm_m.group(1)
    if not re.search(r"^title:\s*\S", fm_body, re.M):
        report.err(rel, 2, "frontmatter", "missing or empty `title:`")
    if not re.search(r"^description:\s*\S", fm_body, re.M):
        report.err(rel, 2, "frontmatter", "missing or empty `description:`")
    return fm_m


def check_hero(path, rel, body, body_line_offset, report):
    head = "\n".join(body.splitlines()[:30])
    hero_m = IMAGE_REF_RE.search(head)
    if not hero_m:
        report.err(
            rel,
            body_line_offset,
            "hero-image",
            "no hero image found in first 30 lines (CONTRIBUTING: every page gets one)",
        )
        return
    alt, src = hero_m.group(1), hero_m.group(2)
    # Compute line number of the hero reference for precise diagnostics.
    prefix_lines = body[: hero_m.start()].count("\n")
    hero_line = body_line_offset + prefix_lines
    if src.endswith(".svg"):
        report.err(rel, hero_line, "hero-image", "hero is SVG — no SVGs for heroes")
    # Resolve image path relative to the file.
    if src.startswith("./"):
        src = src[2:]
    img_path = (path.parent / src).resolve()
    if not img_path.is_file():
        report.err(rel, hero_line, "hero-image", f"image file not found: {src}")
    alt_words = len(alt.split())
    if alt_words < 6:
        report.warn(
            rel,
            hero_line,
            "hero-alt",
            f"alt text has {alt_words} words — wants ≥6 with personality",
        )


def check_emojis(path, rel, body, body_line_offset, report):
    if path.name in EMOJI_ALLOW:
        return
    stripped = CODE_BLOCK_RE.sub(lambda m: "\n" * m.group(0).count("\n"), body)
    stripped = INLINE_CODE_RE.sub("", stripped)
    for i, line in enumerate(stripped.splitlines(), start=body_line_offset):
        if EMOJI_RE.search(line):
            report.err(
                rel,
                i,
                "no-emoji",
                "emoji in prose (CONTRIBUTING: no emojis outside the Holocron portal)",
            )


def check_placeholders(path, rel, body, body_line_offset, report):
    for i, line in enumerate(body.splitlines(), start=body_line_offset):
        lower = line.lower()
        for token in PLACEHOLDER_TOKENS:
            if token.lower() in lower:
                # Allow mentioning the token explicitly in quotes as an
                # anti-example (e.g. "never use YOUR_TOKEN_HERE").
                if f'"{token.lower()}"' in lower or f"`{token.lower()}`" in lower:
                    continue
                report.err(
                    rel,
                    i,
                    "no-placeholder",
                    f"'{token}' in text — CONTRIBUTING wants real values only",
                )


def check_length(path, rel, body, body_line_offset, report):
    clean = CODE_BLOCK_RE.sub("", body)
    clean = IMAGE_REF_RE.sub("", clean)
    clean = INLINE_CODE_RE.sub("", clean)
    # Drop table rows (they read faster than prose; CONTRIBUTING exempts them).
    clean_lines = [ln for ln in clean.splitlines() if not ln.lstrip().startswith("|")]
    words = len(" ".join(clean_lines).split())
    if words > 1200:
        report.warn(
            rel,
            body_line_offset,
            "length",
            f"~{words} prose words — Five-Minute Rule cap is 1200 (tables/code stripped)",
        )


def check_page(path, report):
    try:
        content = path.read_text(encoding="utf-8")
    except Exception as e:
        report.err(path.relative_to(ROOT), 0, "read", str(e))
        return
    rel = path.relative_to(ROOT)

    fm_m = check_frontmatter(path, rel, content, report)
    if not fm_m:
        return

    body_line_offset = body_starts_at(content, fm_m.end())
    body = content[fm_m.end():]

    check_hero(path, rel, body, body_line_offset, report)
    check_emojis(path, rel, body, body_line_offset, report)
    check_placeholders(path, rel, body, body_line_offset, report)
    check_length(path, rel, body, body_line_offset, report)


def main(argv):
    targets = []
    if len(argv) > 1:
        for arg in argv[1:]:
            p = Path(arg)
            if not p.is_absolute():
                p = ROOT / p
            if p.is_file() and p.suffix == ".mdx":
                targets.append(p)
            elif p.is_dir():
                targets.extend(sorted(p.rglob("*.mdx")))
    else:
        targets = sorted(DOCS.rglob("*.mdx"))

    if not targets:
        print("no .mdx files to check", file=sys.stderr)
        return 2

    report = Report()
    for p in targets:
        check_page(p, report)

    for w in report.warnings:
        print(f"warn: {w}")
    for e in report.errors:
        print(f"FAIL: {e}", file=sys.stderr)

    total = len(targets)
    if report.errors:
        print(
            f"\n{len(report.errors)} error(s), {len(report.warnings)} warning(s) "
            f"across {total} page(s) — CONTRIBUTING.md violated",
            file=sys.stderr,
        )
        return 1
    print(
        f"OK — {total} page(s) checked, {len(report.warnings)} warning(s), 0 errors"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
