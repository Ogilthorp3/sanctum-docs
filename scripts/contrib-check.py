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

import hashlib
import re
import sys
from collections import defaultdict
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

# MDX-tag-character pitfall: `<` followed by a digit is interpreted as
# the start of a JSX tag and the parser dies. See check_mdx_tag_chars.
MDX_BAD_LT_RE = re.compile(r'<(\d)')

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

# --- No-Leak rule (CONTRIBUTING §"The No-Leak Rule") --------------------
#
# Match patterns that indicate real operational data leaking into public docs.
# Canonical placeholder ranges are whitelisted so the check doesn't fight the
# fix.

# Real-IP detectors. Scope: only tailnet and public addresses are flagged.
# Private RFC1918 ranges (10.x, 172.16-31.x, 192.168.x) are fine to keep real —
# unroutable from the internet, they teach topology without exposing a target.
LEAK_IP_PATTERNS = [
    # Tailscale range: 100.0.0.0/10. The placeholder `100.0.0.X` sits outside
    # that range (100.0.0.0/24 is public BGP space) so it reads as
    # "tailnet-shaped" without being a real tailnet addr.
    (re.compile(r"\b100\.(6[4-9]|[7-9]\d|1[01]\d|12[0-7])\.\d{1,3}\.\d{1,3}\b"), "tailnet-IP"),
]

# MAC addresses not in the FA:CE:DE:CA:CA:XX documentation block.
# Locally-administered, unicast; spells "face de caca" per the Haus joke.
LEAK_MAC_RE = re.compile(r"\b([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}\b")
ALLOWED_MAC_PREFIX = "FA:CE:DE:CA:CA:"

# Real-username + home-path detector. Any /Users/<name>/ that isn't neo is a leak.
LEAK_USER_PATH_RE = re.compile(r"/Users/(?!neo\b)[A-Za-z][A-Za-z0-9._-]{0,31}/")

# Personal handles — real first names or surnames tied to the operator.
# Service accounts (ubuntu@, operator@, root@) are allowed — generic.
PERSONAL_HANDLE_AT_HOST_RE = re.compile(
    r"\b(bert|bertrand|nepveu)@[A-Za-z0-9.:_-]+",
    re.IGNORECASE,
)

# Phone numbers: allow only the 555-0100..555-0199 fictional block.
LEAK_PHONE_RE = re.compile(r"\+1\s*\d{3}\s*\d{3}\s*\d{4}|\+1\d{10}")
ALLOWED_PHONE_PREFIX = "+1555555"

# Real hostnames. Allow the `.local` placeholders and nothing else.
LEAK_HOSTNAME_RES = [
    # Device naming pattern that exposes the owner's first name.
    re.compile(r"\bBerts?-[A-Za-z0-9-]+\.local\b"),
    # Surname in an instance slug (e.g. "firstname-surname").
    re.compile(r"\b[A-Za-z]+-nepveu\b", re.IGNORECASE),
]
ALLOWED_LOCAL_HOSTS = {"haus.local", "satellite.local", "yoda.local"}

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

# Pages exempt from the unique-hero requirement. 404.mdx is a template
# error page, not content; it carries the splash brand glyph instead.
HERO_EXEMPT = {
    "404.mdx",
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


def check_hero(path, rel, body, body_line_offset, report, fm_text=""):
    if path.name in HERO_EXEMPT:
        return
    # Starlight splash pages put the hero in frontmatter (`template: splash`
    # + `hero.image.{dark,light}`), not as a markdown ![alt](path). Treat
    # that as a valid hero so contrib-check doesn't false-fail homepages.
    if fm_text and re.search(r'^\s*template:\s*splash\s*$', fm_text, re.M) \
       and re.search(r'^\s{2,}image\s*:', fm_text, re.M):
        return

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


def check_no_leak(path, rel, body, body_line_offset, report):
    """Enforce the No-Leak rule from CONTRIBUTING.md."""
    for i, line in enumerate(body.splitlines(), start=body_line_offset):
        # Skip lines that are clearly teaching the rule itself (they quote the
        # sensitive pattern inside backticks for illustration). A backtick-wrapped
        # occurrence is fine; a bare prose occurrence isn't.
        stripped = line.strip()
        if stripped.startswith(("| ", "|")) and "IANA" in line:
            continue  # canonical-placeholder table row

        for rx, kind in LEAK_IP_PATTERNS:
            for m in rx.finditer(line):
                hit = m.group(0)
                # Allow inside inline code.
                before = line[: m.start()]
                after = line[m.end():]
                if before.count("`") % 2 == 1 and after.count("`") >= 1:
                    continue
                report.err(
                    rel, i, "no-leak",
                    f"real {kind} '{hit}' — use 100.0.0.X placeholder",
                )

        for m in LEAK_MAC_RE.finditer(line):
            mac = m.group(0)
            if mac.upper().startswith(ALLOWED_MAC_PREFIX):
                continue
            report.err(
                rel, i, "no-leak",
                f"real MAC '{mac}' — use FA:CE:DE:CA:CA:XX block",
            )

        for m in LEAK_USER_PATH_RE.finditer(line):
            report.err(
                rel, i, "no-leak",
                f"real username in path '{m.group(0)}' — use /Users/neo/ or ~/",
            )

        for m in PERSONAL_HANDLE_AT_HOST_RE.finditer(line):
            report.err(
                rel, i, "no-leak",
                f"personal handle in '{m.group(0)}' — use neo@<HOST>",
            )

        for m in LEAK_PHONE_RE.finditer(line):
            raw = re.sub(r"\s+", "", m.group(0))
            if raw.startswith(ALLOWED_PHONE_PREFIX):
                continue
            report.err(
                rel, i, "no-leak",
                f"real phone number '{m.group(0)}' — use +15555550100 (555-01xx fictional block)",
            )

        for rx in LEAK_HOSTNAME_RES:
            for m in rx.finditer(line):
                report.err(
                    rel, i, "no-leak",
                    f"real hostname '{m.group(0)}' — use <MINI>/<MBP>/haus.local placeholders",
                )


def check_mdx_tag_chars(path, rel, body, body_line_offset, report):
    """Catch `<digit` patterns that break MDX parsing.

    The MDX parser reads `<` as the start of a JSX/HTML tag. The next
    character must be a name-start character (letter, `$`, `_`) or `/`
    (closing tag). A digit, `&`, or other punctuation crashes the build
    with `Unexpected character ... before name`. Symptom: Cloudflare
    Pages deploy fails with a long Vite trace pointing at the offending
    line.

    Catches: bare `<0`..`<9` in prose. Allows the same patterns inside
    fenced code blocks and inline backticks (where MDX doesn't parse
    them as JSX).

    Pinned 2026-04-26 after chitti.mdx broke the deploy: prose said
    `<20%` and the build refused. Workarounds: `&lt;20%`, `` `<20%` ``,
    or rewording to `under 20%`.
    """
    stripped = CODE_BLOCK_RE.sub(lambda m: "\n" * m.group(0).count("\n"), body)
    stripped = INLINE_CODE_RE.sub("", stripped)
    for i, line in enumerate(stripped.splitlines(), start=body_line_offset):
        for m in MDX_BAD_LT_RE.finditer(line):
            ch = m.group(1)
            report.err(
                rel, i, "mdx-tag-chars",
                f"`<{ch}` starts a broken JSX tag — escape as `&lt;{ch}` "
                f"or wrap in backticks (cause of the 2026-04-26 deploy break)",
            )


# ASCII-art box-drawing characters used for diagrams.
# Used by check_ascii_art_alignment to detect "is this code block actually a diagram?"
BOX_DRAWING_CHARS = frozenset('─│┌┐└┘├┤┬┴┼═║╔╗╚╝╠╣╦╩╬')

# Junction characters: when these appear between ┌ and ┐ on a top border,
# the row is a flow-diagram node (branching, joining), not a simple box top.
# Such layouts are too varied to reliably validate from a regex — for those,
# use SVG instead of ASCII art (see CONTRIBUTING.md "Diagrams").
CONNECTOR_CHARS = frozenset('┼┬┴├┤')

# Pages allowed to ship with ASCII-art misalignment (debt). Each entry is
# documented technical debt: fix the diagram in ASCII (most are off-by-1
# border widths) or convert to SVG, then remove from this set. The set is
# currently empty — every diagram in the tree aligns. Adding to it is the
# escape hatch when a diagram is genuinely too varied to ASCII-align.
ASCII_ART_KNOWN_BROKEN = set()

# Code-fence regex — opening or closing ```, optionally with a language tag,
# allowing any leading whitespace (indented fenced blocks).
FENCE_RE = re.compile(r'^\s*```')


def _iter_code_blocks(body, body_line_offset):
    """Yield (first-content-line-num, [body lines]) for each ``` fenced block.

    The line number is 1-indexed in the original file (post-frontmatter
    offset applied), pointing at the first line INSIDE the fence (not the
    fence itself). The body lines are stripped of their trailing newline
    by splitlines() but otherwise preserved verbatim (whitespace intact —
    column counting matters for alignment checks).
    """
    lines = body.splitlines()
    n = len(lines)
    i = 0
    while i < n:
        if FENCE_RE.match(lines[i]):
            i += 1  # past opening fence
            block_start = body_line_offset + i
            block_body = []
            while i < n and not FENCE_RE.match(lines[i]):
                block_body.append(lines[i])
                i += 1
            yield block_start, block_body
            if i < n:
                i += 1  # past closing fence
        else:
            i += 1


def check_ascii_art_alignment(path, rel, body, body_line_offset, report):
    """Verify ASCII-art box edges line up. Apple-grade docs: at all times.

    Only validates *simple* single boxes:

    1. One ┌ and one ┐ on the top row.
    2. No connector chars (┼┬┴├┤) between ┌ and ┐ on the top row.
    3. One └ and one ┘ on the matching bottom row.
    4. No intermediate ┌ row between the matched top and bottom.

    For each simple box: top ┌ col == bottom └ col, top ┐ col == bottom
    ┘ col, and every interior line has │ at both edge columns (anything
    beyond the right │ — annotations like "← above" — is fine).

    Complex layouts — junctions, branching trees, side-by-side boxes —
    are deliberately skipped: too varied to reliably parse from a regex
    without false positives. For those, use SVG instead of ASCII art
    (see CONTRIBUTING.md "Diagrams").

    Catches the 2026-05-24 force-flow.mdx Screen Time diagram bug where
    the content interior was 22 chars but the border interior was 21
    (off-by-one). In fixed-width code blocks every column matters.

    Whitespace-only interior lines are allowed (intentional blank rows).
    Lines without │ but with other content (internal divider rows) are
    skipped — only edge alignment is enforced, not interior structure.
    Tabs in any box-drawing line are flagged separately.

    Pages in ASCII_ART_KNOWN_BROKEN are skipped with a warning — they're
    debt to be paid down (ASCII fix or SVG conversion).
    """
    if str(rel) in ASCII_ART_KNOWN_BROKEN:
        report.warn(
            rel, body_line_offset, "ascii-art-deferred",
            "page is on ASCII_ART_KNOWN_BROKEN — alignment check skipped. "
            "Fix the misalignment in ASCII or convert to SVG, then remove "
            "from the set in contrib-check.py.",
        )
        return
    for block_start, block_body in _iter_code_blocks(body, body_line_offset):
        # Skip non-diagram blocks — no box characters anywhere.
        if not any(c in BOX_DRAWING_CHARS for line in block_body for c in line):
            continue

        # Flag tabs in any box-drawing line — they break column counting.
        for k, line in enumerate(block_body):
            if '\t' in line and any(c in BOX_DRAWING_CHARS for c in line):
                report.err(
                    rel, block_start + k, "ascii-art",
                    "tab character in a box-drawing line — use spaces only "
                    "(tabs render at variable widths and destroy alignment)",
                )

        # Walk lines, pairing each ┌...┐ top-border with the next └...┘.
        n = len(block_body)
        i = 0
        while i < n:
            line = block_body[i]
            if '┌' in line and '┐' in line:
                # Skip multi-box rows — side-by-side boxes can't be paired
                # reliably without a full diagram parser; SVG territory.
                if line.count('┌') > 1 or line.count('┐') > 1:
                    i += 1
                    continue
                top_l = line.index('┌')
                top_r = line.index('┐')
                if top_r <= top_l:
                    i += 1
                    continue
                # Skip junction tops — ┌...┐ with ┼┬┴├┤ between corners
                # is a flow-diagram node (branching, joining), not a box.
                if any(c in CONNECTOR_CHARS for c in line[top_l + 1:top_r]):
                    i += 1
                    continue

                # Find the matching bottom border. If another ┌ appears
                # first, this top is part of a nested/branching layout —
                # skip; let any inner box be checked on its own pass.
                bot_idx = None
                for j in range(i + 1, n):
                    if '┌' in block_body[j]:
                        break
                    if '└' in block_body[j] and '┘' in block_body[j]:
                        bot_idx = j
                        break
                if bot_idx is None:
                    i += 1
                    continue

                bot_line = block_body[bot_idx]
                # Skip multi-box bottoms too — same rationale as the top.
                if bot_line.count('└') > 1 or bot_line.count('┘') > 1:
                    i += 1
                    continue
                bot_l = bot_line.index('└')
                bot_r = bot_line.index('┘')

                if bot_l != top_l:
                    report.err(
                        rel, block_start + bot_idx, "ascii-art",
                        f"box bottom '└' at col {bot_l + 1} but top '┌' at "
                        f"col {top_l + 1} — misaligned left edge",
                    )
                if bot_r != top_r:
                    report.err(
                        rel, block_start + bot_idx, "ascii-art",
                        f"box bottom '┘' at col {bot_r + 1} but top '┐' at "
                        f"col {top_r + 1} — misaligned right edge",
                    )

                # Interior edge checks.
                for k in range(i + 1, bot_idx):
                    mid = block_body[k]
                    if mid.strip() == "":
                        continue  # blank row inside box — allowed
                    if '│' not in mid:
                        continue  # connector / divider line — not edge-relevant
                    # Allow ├ at the left edge (and ┤ at the right) — those
                    # are valid tee characters for a divider row inside a box.
                    actual_l = mid[top_l] if top_l < len(mid) else '(EOL)'
                    if actual_l not in ('│', '├'):
                        report.err(
                            rel, block_start + k, "ascii-art",
                            f"box left edge expects '│' or '├' at col "
                            f"{top_l + 1}, got '{actual_l}'",
                        )
                    actual_r = mid[top_r] if top_r < len(mid) else '(EOL)'
                    if actual_r not in ('│', '┤'):
                        report.err(
                            rel, block_start + k, "ascii-art",
                            f"box right edge expects '│' or '┤' at col "
                            f"{top_r + 1}, got '{actual_r}'",
                        )

                i = bot_idx + 1
            else:
                i += 1


def collect_all_heroes():
    """Walk every .mdx under docs/ and return (page_rel_path, hero_abs_path) tuples.

    Always runs against the full repo (not just the targets passed on the CLI),
    because rule-1 is a cross-page invariant: a hero shared by two pages is a
    violation even when only one of them is being checked.
    """
    pairs = []
    for p in sorted(DOCS.rglob("*.mdx")):
        try:
            content = p.read_text(encoding="utf-8")
        except Exception:
            continue
        fm_m = FRONTMATTER_RE.match(content)
        if not fm_m:
            continue
        fm_text = fm_m.group(1)
        if re.search(r'^\s*template:\s*splash\s*$', fm_text, re.M) and \
           re.search(r'^\s{2,}image\s*:', fm_text, re.M):
            continue
        body = content[fm_m.end():]
        head = "\n".join(body.splitlines()[:30])
        m = IMAGE_REF_RE.search(head)
        if not m:
            continue
        src = m.group(2)
        if src.startswith(("http://", "https://")):
            continue
        if src.startswith("./"):
            src = src[2:]
        img = (p.parent / src).resolve()
        pairs.append((p.relative_to(ROOT), img))
    return pairs


def check_heroes_unique(report):
    """Flag any hero referenced by 2+ pages.

    Rule #1 (CONTRIBUTING.md): every page gets a UNIQUE hero. Reusing one
    across pages signals a generation step got skipped.
    """
    by_hero = defaultdict(list)
    for page, hero in collect_all_heroes():
        by_hero[hero].append(str(page))
    for hero, pages in by_hero.items():
        if len(pages) < 2:
            continue
        try:
            hero_rel = hero.relative_to(ROOT)
        except ValueError:
            hero_rel = hero
        for page in pages:
            report.err(
                page, 0, "hero-unique",
                f"hero `{hero_rel}` is shared by {len(pages)} pages "
                f"({', '.join(sorted(pages))}) — rule #1 wants a unique hero per page",
            )


def check_image_files_on_disk(report):
    """Detect orphan image files, byte-identical duplicates, and Finder-suffix names.

    Walks src/content/docs/**/images/* and reports:
    - Orphans: file is not referenced by any .mdx (warn — clean up or assign)
    - Byte-dups: two+ files with identical sha256 (err — pick one canonical home)
    - Suffix names: ` 2.`, `-1.`, ` copy.`, `_copy.`, `(1).` patterns (warn)
    """
    image_exts = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
    image_files = []
    for img_dir in DOCS.rglob("images"):
        if not img_dir.is_dir():
            continue
        for f in img_dir.iterdir():
            if f.is_file() and f.suffix.lower() in image_exts:
                image_files.append(f)

    referenced = set()
    for p in DOCS.rglob("*.mdx"):
        try:
            text = p.read_text(encoding="utf-8")
        except Exception:
            continue
        for m in IMAGE_REF_RE.finditer(text):
            src = m.group(2)
            if src.startswith(("http://", "https://")):
                continue
            if src.startswith("./"):
                src = src[2:]
            referenced.add((p.parent / src).resolve())

    for f in image_files:
        if f.resolve() not in referenced:
            report.warn(
                str(f.relative_to(ROOT)), 0, "hero-orphan",
                "image is not referenced by any .mdx — clean up or assign to a page",
            )

    by_hash = defaultdict(list)
    for f in image_files:
        try:
            h = hashlib.sha256(f.read_bytes()).hexdigest()
        except Exception:
            continue
        by_hash[h].append(f)
    for files in by_hash.values():
        if len(files) < 2:
            continue
        rels = sorted(str(f.relative_to(ROOT)) for f in files)
        for f in files:
            report.err(
                str(f.relative_to(ROOT)), 0, "hero-bytedup",
                f"byte-identical to {len(files) - 1} other file(s): "
                f"{', '.join(r for r in rels if r != str(f.relative_to(ROOT)))} "
                f"— pick one canonical home",
            )

    # Only Finder-canonical duplicate patterns: ` 2.png`, ` copy.png`, `(1).png`.
    # `-N.` is too common in legitimate names (`hero-slice-4.png`, `v1-snapshot.png`).
    suffix_re = re.compile(r"( \d+\.| copy\.|_copy\.|\(\d+\)\.)")
    for f in image_files:
        if suffix_re.search(f.name):
            report.warn(
                str(f.relative_to(ROOT)), 0, "hero-suffix",
                f"filename '{f.name}' looks like a Finder duplicate — rename or remove",
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

    check_hero(path, rel, body, body_line_offset, report, fm_m.group(1))
    check_emojis(path, rel, body, body_line_offset, report)
    check_placeholders(path, rel, body, body_line_offset, report)
    check_no_leak(path, rel, body, body_line_offset, report)
    check_mdx_tag_chars(path, rel, body, body_line_offset, report)
    check_ascii_art_alignment(path, rel, body, body_line_offset, report)
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

    # Cross-page invariants — always run against the full docs/ tree, even
    # when the CLI passed a single-file target. Hero uniqueness is a global
    # property; a single-file check can't see its own violations.
    check_heroes_unique(report)
    check_image_files_on_disk(report)

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
